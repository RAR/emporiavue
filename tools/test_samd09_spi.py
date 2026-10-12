#!/usr/bin/env python3
"""Host fault-injection tests for the actual shared SAMD09 SPI functions.

Run: python3 tools/test_samd09_spi.py
Requires a C++ compiler. MMIO/interrupts are simulated; hardware timing is not.
Only ARM barriers and 32-bit peripheral-address casts are adapted for the host.
"""
from pathlib import Path
import os
import re
import shlex
import subprocess
import tempfile


SOURCE = Path(__file__).resolve().parents[1] / "firmware/samd09/main_spi.c"


def function(source: str, name: str) -> str:
    match = re.search(rf"^(?:static )?(?:void|bool|uint8_t) {name}\([^;]*?\)\n\{{", source, re.M)
    if match is None:
        raise AssertionError(f"Function not found: {name}")
    depth = 1
    end = match.end()
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[match.start():end]


MOCKS = r"""
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <deque>

// SAMD INTFLAG/STATUS registers clear bits written as one.
struct W1C {
    uint16_t value = 0;
    operator uint16_t() const { return value; }
    void operator=(uint16_t bits) { value &= ~bits; }
};
W1C REG_ADC_INTFLAG, REG_TC1_INTFLAG, REG_DMAC_CHINTFLAG;
uint16_t REG_TC1_CTRLA = 2;
uint8_t REG_TC1_STATUS = 0, REG_ADC_STATUS = 0, REG_ADC_CTRLA = 2;
uint8_t REG_DMAC_CHID = 0, REG_DMAC_CHCTRLA = 2;
uint16_t REG_ADC_RESULT = 0;
uint32_t REG_PORT_OUT = 0, REG_PORT_OUTSET = 0, REG_PORT_OUTCLR = 0;
#define STATUS_SYNCBUSY_BIT 0x80
unsigned adc_resets = 0;
unsigned adc_pin_offset = 3;
void adc_config() {
    assert(!(REG_TC1_CTRLA & 2));
    assert(!(REG_ADC_CTRLA & 2));
    assert(REG_DMAC_CHCTRLA == 0);
    adc_pin_offset = 0;
    ++adc_resets;
}

unsigned primask = 0;
void (*after_snapshot)() = nullptr;
uint32_t spi_enter_critical() {
    unsigned previous = primask;
    primask = 1;
    return previous;
}
void spi_exit_critical(uint32_t previous) {
    primask = previous;
    if (!primask && after_snapshot) {
        auto callback = after_snapshot;
        after_snapshot = nullptr;
        callback();
    }
}

#ifdef EMPORIAVUE_TARGET_VUE3
W1C REG_SERCOM0_STATUS, REG_SERCOM0_INTFLAG;
std::deque<uint8_t> uart_fifo;
uint16_t read_uart_data() {
    assert(!uart_fifo.empty()); // DATA may only be read with RXC set.
    uint8_t value = uart_fifo.front();
    uart_fifo.pop_front();
    if (uart_fifo.empty()) REG_SERCOM0_INTFLAG.value &= ~4U;
    return value;
}
#define REG_SERCOM0_DATA read_uart_data()
#endif
"""


TESTS = r"""
void reset_stream() {
    SpiBuildFrameIndex = SpiReadyHead = SpiReadyCount = SpiBuildScanIndex = 0;
    SpiFrameSequence = SpiPendingFlags = 0;
    SpiSampleCounter = SpiFrameOverruns = 0;
    DMAresultIndex = MuxCounter = 0;
    DiscardNextAdcScan = false;
    dmabool = true;
    REG_ADC_INTFLAG.value = 0;
    REG_TC1_CTRLA = REG_ADC_CTRLA = REG_DMAC_CHCTRLA = 2;
    adc_resets = 0;
    adc_pin_offset = 3;
}

void test_adc_startup() {
    reset_stream();
    REG_PORT_OUT = 0x80c00000; // Preserve FRAME/CS and unrelated output states.
    prepare_adc_scan_start();
    assert((REG_PORT_OUT & 0x1030000) == outputpinTable[0]);
    assert((REG_PORT_OUT & ~0x1030000U) == 0x80c00000U);
    assert(DiscardNextAdcScan);
    handle_adc_dma_interrupt(DMA_INT_TRANSFER_COMPLETE);
    assert(!DiscardNextAdcScan && MuxCounter == 0 && SpiSampleCounter == 0);
}

void test_queue_error_retention() {
    reset_stream();
    finalize_spi_frame();
    finalize_spi_frame();
    assert(SpiReadyCount == SPI_READY_QUEUE_CAPACITY);
    const uint8_t active = SpiReadyFrameIndex[SpiReadyHead];
    const uint16_t active_sequence = SpiFrames[active].header.sequence;
    SpiPendingFlags = SPI_FLAG_DMA_ERROR | SPI_FLAG_VOLTAGE_ERROR | SPI_FLAG_ADC_OVERRUN;
    finalize_spi_frame();
    finalize_spi_frame();
    const uint16_t errors = SPI_FLAG_OVERRUN | SPI_FLAG_DMA_ERROR |
        SPI_FLAG_VOLTAGE_ERROR | SPI_FLAG_ADC_OVERRUN;
    assert(SpiPendingFlags == errors);
    assert(SpiFrameOverruns == 2 && SpiFrameSequence == 4);
    assert(SpiReadyCount == SPI_READY_QUEUE_CAPACITY);
    assert(SpiFrames[active].header.sequence == active_sequence);
    // Release one TX slot, then accept a frame carrying all retained errors.
    SpiReadyHead = (SpiReadyHead + 1) % SPI_READY_QUEUE_CAPACITY;
    --SpiReadyCount;
    const uint8_t accepted = SpiBuildFrameIndex;
    finalize_spi_frame();
    assert(SpiPendingFlags == 0 && SpiFrameSequence == 5);
    assert((SpiFrames[accepted].header.flags & errors) == errors);
#ifdef EMPORIAVUE_TARGET_VUE3
    assert(((SpiFrames[accepted].header.flags & 0x7ff8) >> 3) == SPI_SAMPLE_PERIOD_TICKS);
#endif
    assert(!spi_ready_queue_contains(SpiBuildFrameIndex));
}

#ifdef EMPORIAVUE_TARGET_VUE3
void feed_byte(uint8_t byte) {
    uart_fifo.push_back(byte);
    REG_SERCOM0_INTFLAG.value |= SERCOM_INT_RXC;
    irq_handler_sercom0();
}
void feed_packet(int16_t a = 123, int16_t b = -456, int16_t c = 789) {
    const int16_t values[] = {a, b, c};
    for (uint8_t phase = 0; phase < 3; ++phase) {
        const uint16_t raw = values[phase] & 0xfff;
        feed_byte(0xc0 | (raw >> 6));
        feed_byte((phase << 6) | (raw & 0x3f));
    }
}
void reset_uart() {
    uart_fifo.clear();
    REG_SERCOM0_STATUS.value = REG_SERCOM0_INTFLAG.value = 0;
    VoltagePacketBuildLength = 0;
    VoltagePacketGeneration = VoltagePacketConsumedGeneration = 0;
    VoltageUartErrors = VoltageRejectedTelegrams = VoltageTelegramUpdates = VoltageAgeScans = 0;
    VoltageValuesValid = false;
    after_snapshot = nullptr;
    primask = 0;
}
void test_uart_errors() {
    // Each hardware error, including combined errors, releases partial reception
    // and is counted without invalidating the last accepted voltage snapshot.
    for (uint16_t errors = 1; errors <= USART_STATUS_RX_ERRORS; ++errors) {
        reset_stream();
        reset_uart();
        feed_packet();
        assert(decode_vue3_voltage_packet());
        assert(DecodedVoltage[0] == 123 && DecodedVoltage[1] == -456 && DecodedVoltage[2] == 789);
        feed_byte(0xc0);
        uart_fifo.push_back(1);
        uart_fifo.push_back(2);
        REG_SERCOM0_STATUS.value = errors;
        REG_SERCOM0_INTFLAG.value = SERCOM_INT_RXC | SERCOM_INT_ERROR;
        irq_handler_sercom0();
        assert(uart_fifo.empty() && REG_SERCOM0_STATUS.value == 0);
        assert(REG_SERCOM0_INTFLAG.value == 0 && VoltageUartErrors == 1);
        assert(VoltagePacketBuildLength == 0 && SpiPendingFlags == 0);
        // An error discards the concurrent telegram but keeps the last known-good
        // voltage snapshot active.
        feed_packet(10, 20, 30);
        handle_adc_dma_interrupt(DMA_INT_TRANSFER_COMPLETE);
        assert(!(SpiPendingFlags & SPI_FLAG_VOLTAGE_ERROR));
        assert(DecodedVoltage[0] == 10 && DecodedVoltage[1] == 20 && DecodedVoltage[2] == 30);
    }
    reset_uart();
    irq_handler_sercom0(); // No RXC: must not read DATA.
    REG_SERCOM0_INTFLAG.value = SERCOM_INT_ERROR;
    irq_handler_sercom0(); // Error IRQ without a byte must clear safely.
    assert(VoltageUartErrors == 1 && REG_SERCOM0_INTFLAG.value == 0);
    assert(!decode_vue3_voltage_packet());
    feed_byte(0x01); // Ignore bytes before a start marker.
    assert(VoltagePacketBuildLength == 0);
    feed_byte(0xc0);
    assert(!decode_vue3_voltage_packet()); // Partial telegram.
    assert(VoltagePacketBuildLength == 1); // Partial reception survives ADC reads.
    reset_uart();
    feed_packet();
    VoltagePacketPublished[3] &= 0x3f; // Duplicate phase 0.
    assert(!decode_vue3_voltage_packet());
    feed_packet();
    VoltagePacketPublished[3] |= 0xc0; // Invalid phase 3.
    assert(!decode_vue3_voltage_packet());
    feed_packet(-2048, 2047, -1);
    assert(decode_vue3_voltage_packet());
    assert(DecodedVoltage[0] == -2048 && DecodedVoltage[1] == 2047 && DecodedVoltage[2] == -1);
    assert(VoltageRejectedTelegrams == 2);
    // No revalidation when nothing was published, even after malformed data.
    assert(decode_vue3_voltage_packet());
    assert(VoltageRejectedTelegrams == 2);

    // Invalid completed telegrams are rejected by the ADC-side consumer. A
    // later valid telegram is then accepted normally.
    for (uint8_t bad_phase : {uint8_t(0), uint8_t(3)}) {
        reset_uart();
        const uint8_t malformed[] = {0xc0, 1, 0xc0, uint8_t(bad_phase << 6), 0xc0, 0x80};
        for (uint8_t byte : malformed) feed_byte(byte);
        assert(!decode_vue3_voltage_packet());
        assert(!VoltageValuesValid);
        assert(VoltageRejectedTelegrams == 1);
        feed_packet();
        assert(decode_vue3_voltage_packet());
    }
}
void inject_next_packet() { feed_packet(10, 20, 30); }
void inject_uart_error() {
    REG_SERCOM0_STATUS.value = 2;
    REG_SERCOM0_INTFLAG.value = SERCOM_INT_ERROR;
    irq_handler_sercom0();
}
void test_uart_snapshot() {
    reset_uart();
    feed_packet();
    after_snapshot = inject_next_packet;
    assert(decode_vue3_voltage_packet());
    assert(DecodedVoltage[0] == 123 && DecodedVoltage[1] == -456);
    assert(decode_vue3_voltage_packet());
    assert(DecodedVoltage[0] == 10 && DecodedVoltage[1] == 20);
    feed_packet();
    after_snapshot = inject_uart_error;
    assert(decode_vue3_voltage_packet()); // Local snapshot stays intact.
    feed_packet();
    assert(decode_vue3_voltage_packet()); // New error keeps the valid snapshot.
    assert(DecodedVoltage[0] == 123 && DecodedVoltage[1] == -456);
    feed_packet();
    primask = 1;
    assert(decode_vue3_voltage_packet());
    assert(primask == 1); // Restore prior mask rather than enabling IRQs blindly.
    primask = 0;
}

void test_uart_scan_boundaries() {
    const uint8_t next_packet[] = {0xc0, 10, 0xc0, 0x40 | 20, 0xc0, 0x80 | 30};
    for (unsigned split = 1; split < 6; ++split) {
        reset_stream(); reset_uart();
        feed_packet();
        assert(decode_vue3_voltage_packet());
        for (unsigned i=0; i<split; ++i) feed_byte(next_packet[i]);
        handle_adc_dma_interrupt(DMA_INT_TRANSFER_COMPLETE);
        assert(VoltagePacketBuildLength == split);
        assert(!(SpiPendingFlags & SPI_FLAG_VOLTAGE_ERROR));
        assert(DecodedVoltage[0] == 123); // Partial data never replaces the snapshot.
        for (unsigned i=split; i<6; ++i) feed_byte(next_packet[i]);
        assert(decode_vue3_voltage_packet());
        assert(DecodedVoltage[0] == 10 && DecodedVoltage[1] == 20 && DecodedVoltage[2] == 30);

        // Before initial acquisition, a partial telegram remains invalid.
        reset_stream(); reset_uart();
        for (unsigned i=0; i<split; ++i) feed_byte(next_packet[i]);
        assert(!decode_vue3_voltage_packet());
        assert(VoltagePacketBuildLength == split);
        for (unsigned i=split; i<6; ++i) feed_byte(next_packet[i]);
        assert(decode_vue3_voltage_packet());
        assert(DecodedVoltage[2] == 30);
    }

    reset_stream(); reset_uart();
    feed_packet(1,2,3);
    feed_packet(10,20,30); // Latest complete publication replaces older pending data.
    assert(decode_vue3_voltage_packet());
    assert(DecodedVoltage[0] == 10 && DecodedVoltage[2] == 30);
    assert(VoltageTelegramUpdates == 1);
    assert(decode_vue3_voltage_packet());
    for (unsigned i=0; i<300; ++i) {
        assert(decode_vue3_voltage_packet()); // Last known-good remains active.
        assert(DecodedVoltage[0] == 10 && DecodedVoltage[2] == 30);
    }
    feed_packet(100,200,300);
    assert(decode_vue3_voltage_packet());
    assert(DecodedVoltage[0] == 100);
    assert(VoltageTelegramUpdates == 2);

    // Partial telegrams survive any number of ADC boundaries and never replace
    // or invalidate an established snapshot until they are complete.
    reset_stream(); reset_uart();
    feed_packet(1,2,3);
    assert(decode_vue3_voltage_packet());
    feed_byte(next_packet[0]);
    for(unsigned scan=0; scan<300; ++scan) {
        handle_adc_dma_interrupt(DMA_INT_TRANSFER_COMPLETE);
        assert(VoltagePacketBuildLength == 1 && VoltageValuesValid);
    }
    assert(VoltageAgeScans == 300);
    assert(DecodedVoltage[0] == 1 && DecodedVoltage[2] == 3);
    for(unsigned i=1; i<6; ++i) feed_byte(next_packet[i]);
    assert(decode_vue3_voltage_packet());
    assert(DecodedVoltage[0] == 10 && DecodedVoltage[2] == 30);
    assert(VoltageAgeScans == 0);
    VoltageAgeScans = UINT32_MAX;
    handle_adc_dma_interrupt(DMA_INT_TRANSFER_COMPLETE);
    assert(VoltageAgeScans == UINT32_MAX); // Diagnostic age saturates, never wraps.
    VoltagePacketConsumedGeneration = VoltagePacketGeneration = UINT32_MAX;
    feed_packet(100,200,300);
    assert(VoltagePacketGeneration == 0 && decode_vue3_voltage_packet());
    assert(DecodedVoltage[0] == 100); // Generation wrap remains observable.
}

void test_uart_clock_slip() {
    // Discrete event simulation, using the actual UART and ADC ISR functions.
    // UART byte spacing is approximately 5.714 us at 1.75 Mbaud; start-to-start
    // telegram spacing is a separate independent variable. The 51 us nominal
    // packet schedule is inherited from the earlier test, NOT a hardware
    // measurement. Sweep equal clocks, drift and faster/slower packet streams.
    // Changing values must actually arrive; a forever-reused cache cannot pass.
    const uint64_t adc_ns = uint64_t(SPI_SAMPLE_PERIOD_TICKS) * 1000 / 16;
    const uint64_t byte_ns = 5714;
    for (uint64_t nominal_packet_ns : {adc_ns, uint64_t(40000), uint64_t(80000), uint64_t(120000)}) {
      for (int ppm : {-5000, -1800, 0, 1800, 5000}) {
        const uint64_t packet_ns = nominal_packet_ns * (1000000 + ppm) / 1000000;
        for (unsigned phase=0; phase<16; ++phase) {
            reset_stream(); reset_uart();
            uint64_t packet_start = adc_ns * phase / 16;
            uint64_t next_byte = packet_start;
            unsigned byte = 0, frames = 0, telegram = 1, updates = 0;
            uint8_t packet[6]{};
            int16_t previous_value = -1;
            uint64_t last_update = 0, longest_gap = 0;
            bool acquired = false;
            for (unsigned scan=0; scan<20000; ++scan) {
                const uint64_t adc_time = uint64_t(scan + 1) * adc_ns;
                while (next_byte <= adc_time) {
                    if (byte == 0) {
                        for(unsigned phase=0; phase<3; ++phase) {
                            const uint16_t raw = telegram % 2000;
                            packet[phase*2] = 0xc0 | (raw >> 6);
                            packet[phase*2+1] = (phase << 6) | (raw & 0x3f);
                        }
                    }
                    feed_byte(packet[byte++]);
                    if (byte == 6) {
                        byte = 0;
                        ++telegram;
                        packet_start += packet_ns;
                    }
                    next_byte = packet_start + byte * byte_ns;
                }
                handle_adc_dma_interrupt(DMA_INT_TRANSFER_COMPLETE);
                if (VoltageValuesValid && DecodedVoltage[0] != previous_value) {
                    previous_value = DecodedVoltage[0];
                    last_update = adc_time;
                    ++updates;
                }
                if (VoltageValuesValid && adc_time - last_update > longest_gap)
                    longest_gap = adc_time - last_update;
                if (VoltageValuesValid) {
                    assert(DecodedVoltage[0] == DecodedVoltage[1]);
                    assert(DecodedVoltage[1] == DecodedVoltage[2]);
                }
                while (SpiReadyCount != 0) {
                    const auto &frame = SpiFrames[SpiReadyFrameIndex[SpiReadyHead]];
                    ++frames;
                    if ((frame.header.flags & SPI_FLAG_VOLTAGE_ERROR) == 0)
                        acquired = true;
                    if (acquired) {
                        assert((frame.header.flags & SPI_FLAG_VOLTAGE_ERROR) == 0);
                    }
                    SpiReadyHead = (SpiReadyHead + 1) % SPI_READY_QUEUE_CAPACITY;
                    --SpiReadyCount;
                }
            }
            assert(frames > 350);
            assert(acquired && updates > 1000);
            assert(longest_gap <= packet_ns + adc_ns);
            assert(VoltageRejectedTelegrams == 0 && VoltageUartErrors == 0);
        }
      }
    }
    std::puts("UART freshness, coherent publication, cached retention and 320 independent clock/phase scenarios passed");
}

uint32_t read_reserved_u32(const SpiRawFrame &frame, unsigned start) {
    uint32_t value=0;
    for(unsigned byte=0;byte<4;++byte)
        value |= uint32_t(frame.scans[start+byte].reserved) << (byte*8);
    return value;
}
bool has_voltage_diagnostics(const SpiRawFrame &frame) {
    return read_reserved_u32(frame,16)==0x44555645 && frame.scans[20].reserved==1;
}
void test_uart_diagnostic_metadata() {
    reset_stream();reset_uart();
    SpiRawFrame old_frame{};
    assert(!has_voltage_diagnostics(old_frame)); // Old all-zero metadata is not decoded.
    VoltageTelegramUpdates=0x12345678;
    VoltageUartErrors=0x87654321;
    VoltageRejectedTelegrams=0xfedcba98;
    VoltageAgeScans=UINT32_MAX;
    const unsigned built=SpiBuildFrameIndex;
    finalize_spi_frame();
    const auto &frame=SpiFrames[built];
    assert(has_voltage_diagnostics(frame));
    assert(read_reserved_u32(frame,0)==VoltageTelegramUpdates);
    assert(read_reserved_u32(frame,4)==VoltageUartErrors);
    assert(read_reserved_u32(frame,8)==VoltageRejectedTelegrams);
    assert(read_reserved_u32(frame,12)==VoltageAgeScans);
    for(unsigned scan=21;scan<SPI_RAW_SCAN_COUNT;++scan)
        assert(frame.scans[scan].reserved==0);
}
#endif

void test_adc_recovery() {
    // Every combination of TERR/TCMPL/SUSP and ADC OVERRUN.
    for (uint8_t flags = 0; flags < 8; ++flags) {
        for (unsigned overrun = 0; overrun < 2; ++overrun) {
            reset_stream();
#ifdef EMPORIAVUE_TARGET_VUE3
            reset_uart();
            feed_packet();
            assert(decode_vue3_voltage_packet());
#endif
            SpiBuildScanIndex = 17;
            SpiSampleCounter = 100;
            REG_ADC_INTFLAG.value = overrun ? ADC_INTFLAG_OVERRUN : 0;
            const bool failed = flags != DMA_INT_TRANSFER_COMPLETE || overrun;
            handle_adc_dma_interrupt(flags);
            if (!failed) {
                assert(adc_resets == 0 && SpiBuildScanIndex == 18);
                assert(SpiSampleCounter == 101 && MuxCounter == 1);
                continue;
            }
            assert(adc_resets == 1 && adc_pin_offset == 0);
            assert(SpiBuildScanIndex == 0 && SpiSampleCounter == 100);
            assert(MuxCounter == 0 && DMAresultIndex == 0 && DiscardNextAdcScan);
            assert(dmabool && REG_DMAC_CHID == DMA_CHANNEL_ADC);
            assert(REG_DMAC_CHCTRLA == DMA_CHANNEL_ENABLE);
            assert(REG_ADC_CTRLA & 2);
            assert(REG_TC1_CTRLA & 2);
            assert(REG_ADC_INTFLAG.value == 0);
            assert(DMAdescriptor[DMA_CHANNEL_ADC].BTCNT == ADC_CHANNEL_COUNT);
            assert(DMAdescriptor[DMA_CHANNEL_ADC].DESCADDR == 0);
            assert(bool(SpiPendingFlags & SPI_FLAG_DMA_ERROR) == (flags != DMA_INT_TRANSFER_COMPLETE));
            assert(bool(SpiPendingFlags & SPI_FLAG_ADC_OVERRUN) == bool(overrun));
            // The first complete post-reset scan is discarded without changing mux.
            handle_adc_dma_interrupt(DMA_INT_TRANSFER_COMPLETE);
            assert(!DiscardNextAdcScan && MuxCounter == 0 && DMAresultIndex == 1);
            assert(SpiBuildScanIndex == 0 && SpiSampleCounter == 100);
#ifdef EMPORIAVUE_TARGET_VUE3
            assert(VoltageValuesValid && VoltagePacketBuildLength == 0);
            assert(decode_vue3_voltage_packet()); // Last known-good survives ADC recovery.
            feed_packet();
#endif
            for (uint8_t channel = 0; channel < ADC_CHANNEL_COUNT; ++channel)
                DMAresults[1][channel] = 1000 + channel;
            handle_adc_dma_interrupt(DMA_INT_TRANSFER_COMPLETE);
            const auto &scan = SpiFrames[SpiBuildFrameIndex].scans[0];
            assert(scan.mux_index == 0 && MuxCounter == 1);
            assert(SpiBuildScanIndex == 1 && SpiSampleCounter == 101);
            assert(SpiFrames[SpiBuildFrameIndex].header.sample_counter == 100);
#ifdef EMPORIAVUE_TARGET_VUE3
            assert(scan.value[0] == 123 && scan.value[1] == 1000);
            assert(scan.value[3] == 1001 && scan.value[5] == 1002);
            assert(scan.value[6] == 1003 && scan.value[7] == 1004);
#else
            for (uint8_t channel = 0; channel < ADC_CHANNEL_COUNT; ++channel)
                assert(scan.value[channel] == 1000 + channel);
#endif
        }
    }
}
int main() {
    test_adc_startup();
    test_queue_error_retention();
    test_adc_recovery();
#ifdef EMPORIAVUE_TARGET_VUE3
    test_uart_errors();
    test_uart_snapshot();
    test_uart_scan_boundaries();
    test_uart_clock_slip();
    test_uart_diagnostic_metadata();
#endif
    std::puts("ADC recovery, queue retention and applicable UART fault tests passed");
}
"""


def main() -> None:
    source = SOURCE.read_text()
    declarations = source[source.index("volatile bool dmabool"):source.index("static uint32_t spi_enter_critical")]
    descriptors = source[source.index("struct DMAdescriptorType {"):source.index("#define __SIZE_OF__")]
    names = [
        "spi_ready_queue_contains", "spi_find_free_build_frame",
        "finalize_spi_frame", "capture_spi_scan",
    ]
    common = "\n".join([
        "#ifdef EMPORIAVUE_TARGET_VUE3",
        function(source, "write_vue3_voltage_diagnostics"),
        "#endif",
        *(function(source, name) for name in names),
    ])
    uart = "\n".join(function(source, name) for name in ["irq_handler_sercom0", "decode_vue3_voltage_packet"])
    adc = "\n".join(function(source, name) for name in ["prepare_adc_scan_start", "enable_adc_dma", "recover_adc_scan", "handle_adc_dma_interrupt"])
    program = "\n".join([
        MOCKS, declarations, descriptors, common,
        "#ifdef EMPORIAVUE_TARGET_VUE3", uart, "#endif", adc, TESTS,
    ])
    program = re.sub(r'__asm__ __volatile__\("dmb sy"(?: ::: "memory")?\);', '(void) 0;', program)
    program = program.replace("(uint32_t) &", "(uint32_t) (uintptr_t) &")
    with tempfile.TemporaryDirectory(prefix="samd09-spi-tests-") as directory:
        for hardware in (2, 3):
            output = Path(directory) / f"vue{hardware}"
            defines = ["-DEMPORIAVUE_TARGET_VUE3=1"] if hardware == 3 else []
            command = shlex.split(os.environ.get("CXX", "c++")) + [
                "-std=c++11", "-O2", "-Wall", "-Wextra", "-Werror", *defines,
                "-x", "c++", "-", "-o", str(output),
            ]
            subprocess.run(command, input=program, text=True, check=True)
            print(f"Vue {hardware}:", flush=True)
            subprocess.run([str(output)], check=True)


if __name__ == "__main__":
    main()
