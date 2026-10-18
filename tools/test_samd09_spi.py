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
    match = re.search(rf"^(?:static )?(?:void|bool|uint8_t) {name}\s*\([^;]*?\)\n\{{", source, re.M)
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

unsigned primask = 0;
bool track_spi_start = false;
bool track_spi_finish = false;
bool finish_expects_cs_release = false;
unsigned spi_entry_primask = 0, spi_critical_depth = 0;
unsigned spi_critical_entries = 0, spi_dma_enables = 0, spi_dma_flag_clears = 0;
unsigned spi_sercom_reads = 0, spi_sercom_flag_clears = 0, spi_sercom_interrupt_disables = 0;
unsigned spi_cs_asserts = 0, spi_cs_deasserts = 0;
bool spi_cs_low = false;
void (*during_spi_guard)() = nullptr;
void (*after_spi_cs_release)() = nullptr;
uint8_t spi_tx_irq_enabled = 0;
unsigned spi_tx_irq_enables = 0, spi_dma_disables = 0;
void assert_spi_setup_unmasked() {
    assert(track_spi_start && spi_critical_depth == 0);
    assert(primask == spi_entry_primask); // Never enable interrupts disabled by the caller.
}

// SAMD INTFLAG/STATUS registers clear bits written as one.
struct W1C {
    uint16_t value = 0;
    operator uint16_t() const { return value; }
    void operator=(uint16_t bits) { value &= ~bits; }
};
W1C REG_ADC_INTFLAG, REG_TC1_INTFLAG;
uint16_t REG_TC1_CTRLA = 2;
uint8_t REG_TC1_STATUS = 0, REG_ADC_STATUS = 0, REG_ADC_CTRLA = 2;
uint8_t REG_DMAC_CHID = 0;
void (*after_adc_dma_enabled)() = nullptr;
struct DmaEnableRegister {
    uint8_t values[2] = {2,0};
    operator uint8_t() const {
        if (track_spi_start) assert(spi_critical_depth == 1 && REG_DMAC_CHID == 1);
        return values[REG_DMAC_CHID];
    }
    DmaEnableRegister &operator=(uint8_t bits) {
        if (track_spi_start) {
            assert(spi_critical_depth == 1 && REG_DMAC_CHID == 1 && spi_cs_low);
            if (bits == 2) ++spi_dma_enables;
        }
        if (track_spi_finish && REG_DMAC_CHID == 1 && bits == 0) {
            // The shared DMA ISR already owns CHID. An error must stop DMA
            // before releasing CS without adding a masked polling section.
            assert(spi_cs_low && spi_critical_depth == 0);
            ++spi_dma_disables;
        }
        values[REG_DMAC_CHID] = bits;
        if (REG_DMAC_CHID == 0 && bits == 2 && after_adc_dma_enabled) after_adc_dma_enabled();
        return *this;
    }
} REG_DMAC_CHCTRLA;
struct DmaInterruptFlags : W1C {
    void operator=(uint16_t bits) {
        if (track_spi_start) {
            assert(spi_critical_depth == 1 && REG_DMAC_CHID == 1);
            ++spi_dma_flag_clears;
        }
        W1C::operator=(bits);
    }
} REG_DMAC_CHINTFLAG;
uint32_t REG_DMAC_BUSYCH = 0, REG_DMAC_PENDCH = 0;

struct SpiInterruptFlags : W1C {
    operator uint16_t() const {
        if (track_spi_start) assert_spi_setup_unmasked();
        return value;
    }
    void operator=(uint16_t bits) {
        if (track_spi_start) { assert_spi_setup_unmasked(); ++spi_sercom_flag_clears; }
        if (track_spi_finish) {
            if (finish_expects_cs_release) assert(!spi_cs_low && spi_cs_deasserts == 1);
            assert(spi_critical_depth == 0);
            ++spi_sercom_flag_clears;
        }
        W1C::operator=(bits);
    }
} REG_SERCOM1_INTFLAG;
struct SpiInterruptDisable {
    uint8_t value = 0;
    void operator=(uint8_t bits) {
        if (track_spi_start) { assert_spi_setup_unmasked(); ++spi_sercom_interrupt_disables; }
        if (track_spi_finish) { assert(spi_critical_depth == 0); ++spi_sercom_interrupt_disables; }
        spi_tx_irq_enabled &= uint8_t(~bits);
        value = bits;
    }
} REG_SERCOM1_INTENCLR;
struct SpiInterruptEnable {
    void operator=(uint8_t bits) {
        assert(track_spi_finish && spi_critical_depth == 0);
        spi_tx_irq_enabled |= bits;
        ++spi_tx_irq_enables;
    }
} REG_SERCOM1_INTENSET;
struct SpiDataRegister {
    operator uint16_t() const {
        if (track_spi_start) { assert_spi_setup_unmasked(); ++spi_sercom_reads; }
        if (track_spi_finish) {
            if (finish_expects_cs_release) assert(!spi_cs_low && spi_cs_deasserts == 1);
            assert(spi_critical_depth == 0);
            ++spi_sercom_reads;
        }
        REG_SERCOM1_INTFLAG.value &= ~4U;
        return 0;
    }
} REG_SERCOM1_DATA;

uint32_t mock_crc = 0;
unsigned crc_begin_calls = 0, crc_byte_calls = 0, crc_end_calls = 0;
void crc32_hardware_begin() {
    assert_spi_setup_unmasked(); ++crc_begin_calls; mock_crc = 0xffffffffU;
}
void crc32_hardware_update_byte(uint8_t value) {
    assert_spi_setup_unmasked(); ++crc_byte_calls; mock_crc ^= value;
    for (unsigned bit=0;bit<8;++bit)
        mock_crc = (mock_crc >> 1) ^ ((mock_crc & 1) ? 0xedb88320U : 0);
}
uint32_t reference_crc32(const uint8_t* bytes, unsigned length) {
    uint32_t crc = 0xffffffffU;
    for (unsigned index=0;index<length;++index) {
        crc ^= bytes[index];
        for (unsigned bit=0;bit<8;++bit) crc = (crc >> 1) ^ ((crc & 1) ? 0xedb88320U : 0);
    }
    return crc ^ 0xffffffffU;
}
uint32_t crc32_hardware_end() {
    assert_spi_setup_unmasked(); ++crc_end_calls; return mock_crc ^ 0xffffffffU;
}
void spi_frame_cs_assert();
void spi_frame_cs_deassert();
uint16_t REG_ADC_RESULT = 0;
uint32_t REG_PORT_OUT = 0, REG_PORT_OUTSET = 0, REG_PORT_OUTCLR = 0;
uint32_t REG_NVMCTRL_CTRLB = 0;
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

void (*after_snapshot)() = nullptr;
uint32_t spi_enter_critical() {
    if (track_spi_start || track_spi_finish) {
        assert(spi_critical_depth == 0);
        ++spi_critical_depth;
        ++spi_critical_entries;
    }
    unsigned previous = primask;
    primask = 1;
    return previous;
}
void spi_exit_critical(uint32_t previous) {
    if (track_spi_start || track_spi_finish) {
        assert(spi_critical_depth == 1);
        --spi_critical_depth;
    }
    primask = previous;
    if (!primask && after_snapshot) {
        auto callback = after_snapshot;
        after_snapshot = nullptr;
        callback();
    }
}
unsigned ram_sleep_calls = 0;
void sleep_and_restore_interrupts_from_ram(uint32_t previous) {
    assert(primask == 1); // Queue check and WFI entry form one masked section.
    ++ram_sleep_calls;
    spi_exit_critical(previous);
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
void test_sleep_decision() {
    // Vue 3 must never execute WFI (emporiavue#9): the idle wait neither sleeps nor masks.
    after_snapshot=nullptr;
    for(unsigned previous : {0U,1U}) {
        for(unsigned active : {0U,1U}) {
            for(unsigned ready=0;ready<=SPI_READY_QUEUE_CAPACITY;++ready) {
                primask=previous; ram_sleep_calls=0;
                SpiTxActive=active; SpiReadyCount=ready;
                wait_for_spi_work();
                assert(ram_sleep_calls==0);
                assert(primask==previous);
            }
        }
    }
    primask=0;
}

void test_flash_sleep_configuration() {
    // Reproduce main's temporary startup setting, then the final NVM setup.
    // Changing only main's first write would fail this regression test.
    for(uint32_t initial : {uint32_t(6),uint32_t(0x306),uint32_t(0xffffffff)}) {
        REG_NVMCTRL_CTRLB=initial;
        Config_NVMCTRL();
        assert(REG_NVMCTRL_CTRLB==0x82);
        assert(((REG_NVMCTRL_CTRLB>>8)&3)==0); // Flash may sleep; SRAM WFI workaround remains.
        assert(((REG_NVMCTRL_CTRLB>>1)&15)==1); // Existing runtime wait states retained.
        assert(REG_NVMCTRL_CTRLB&(1U<<7)); // Manual writes retained.
        assert(!(REG_NVMCTRL_CTRLB&(1U<<18))); // Cache remains enabled.
    }
    std::puts("SRAM wake retained: Flash may sleep; MANW/RWS/cache unchanged");
}

void reset_stream() {
    assert(!track_spi_start);
    after_adc_dma_enabled = nullptr;
    SpiBuildFrameIndex = SpiReadyHead = SpiReadyCount = SpiBuildScanIndex = 0;
    SpiFrameSequence = SpiPendingFlags = 0;
    SpiSampleCounter = 0;
    DMAresultIndex = MuxCounter = 0;
    DiscardNextAdcScan = false;
    dmabool = true;
    REG_ADC_INTFLAG.value = 0;
    REG_DMAC_CHID = DMA_CHANNEL_ADC;
    REG_TC1_CTRLA = REG_ADC_CTRLA = REG_DMAC_CHCTRLA = 2;
    adc_resets = 0;
    adc_pin_offset = 3;
}

void spi_frame_cs_assert() {
    assert_spi_setup_unmasked();
    ++spi_cs_asserts;
    assert(!spi_cs_low);
    spi_cs_low = true;
    if (during_spi_guard && primask == 0) during_spi_guard();
}
void spi_frame_cs_deassert() {
    if (track_spi_start) assert_spi_setup_unmasked();
    else assert(track_spi_finish && spi_critical_depth == 0);
    ++spi_cs_deasserts;
    assert(spi_cs_low);
    spi_cs_low = false;
    if (after_spi_cs_release && primask == 0) after_spi_cs_release();
}

void reset_spi_start(unsigned previous) {
    track_spi_start = false;
    track_spi_finish = false;
    reset_stream();
    SpiTxActive = SpiTxAwaitingComplete = false;
    SpiReadyFrameIndex[0] = 1;
    SpiReadyFrameIndex[1] = 2;
    SpiReadyCount = 1;
    SpiBuildFrameIndex = 0;
    for (unsigned index=0;index<SPI_FRAME_SIZE;++index)
        reinterpret_cast<uint8_t*>(&SpiFrames[1])[index] = uint8_t(index * 37 + 11);
    REG_DMAC_CHCTRLA.values[DMA_CHANNEL_SPI_TX] = 0;
    REG_DMAC_BUSYCH = REG_DMAC_PENDCH = 0;
    REG_DMAC_CHINTFLAG.value = 7;
    REG_SERCOM1_INTFLAG.value = SERCOM_INT_TXC | SERCOM_INT_RXC;
    REG_SERCOM1_INTENCLR.value = 0;
    spi_critical_depth = spi_critical_entries = spi_dma_enables = spi_dma_flag_clears = 0;
    spi_sercom_reads = spi_sercom_flag_clears = spi_sercom_interrupt_disables = 0;
    spi_cs_asserts = spi_cs_deasserts = 0;
    crc_begin_calls = crc_byte_calls = crc_end_calls = 0;
    during_spi_guard = after_snapshot = nullptr;
    after_spi_cs_release = nullptr;
    spi_cs_low = false;
    primask = spi_entry_primask = previous;
    track_spi_start = true;
}

void simulate_adc_during_spi_guard() {
    assert(primask == 0 && spi_critical_depth == 0 && spi_cs_low);
    // An ADC interrupt selects its DMA channel and may append a new frame.
    // SPI startup must reselect channel 1 *after* this unmasked guard period.
    REG_DMAC_CHID = DMA_CHANNEL_ADC;
    SpiReadyCount = 2;
}

void test_spi_start_critical_scope() {
    for (unsigned previous : {0U,1U}) {
        for (unsigned preempt : {0U,1U}) {
            reset_spi_start(previous);
            if (preempt) during_spi_guard = simulate_adc_during_spi_guard;
            start_spi_dma_if_ready();
            assert(primask == previous && spi_critical_depth == 0);
            assert(spi_critical_entries == 1 && spi_dma_enables == 1 && spi_dma_flag_clears == 1);
            assert(spi_sercom_interrupt_disables == 1 && spi_sercom_flag_clears == 1 && spi_sercom_reads == 1);
            assert(spi_cs_asserts == 1 && spi_cs_deasserts == 0 && spi_cs_low);
            assert(SpiFrames[1].crc32 == reference_crc32((const uint8_t*) &SpiFrames[1], SPI_FRAME_SIZE-SPI_CRC_SIZE));
            assert(SpiTxActive && !SpiTxAwaitingComplete && SpiPendingFlags == 0);
            assert(SpiReadyHead == 0 && SpiReadyFrameIndex[0] == 1);
            assert(SpiReadyCount == ((preempt && !previous) ? 2 : 1));
            assert(REG_DMAC_CHID == DMA_CHANNEL_SPI_TX);
            assert(REG_DMAC_CHCTRLA.values[DMA_CHANNEL_ADC] == DMA_CHANNEL_ENABLE);
            const auto &descriptor = DMAdescriptor[DMA_CHANNEL_SPI_TX];
            assert(descriptor.BTCTRL == 0x409 && descriptor.BTCNT == SPI_FRAME_SIZE);
            assert(descriptor.SRCADDR == uint32_t(uintptr_t(&SpiFrames[1])) + SPI_FRAME_SIZE);
            assert(descriptor.DSTADDR == uint32_t(uintptr_t(&REG_SERCOM1_DATA)) && descriptor.DESCADDR == 0);
            track_spi_start = false;
        }

        // Every independent busy condition must leave the frame queued and CS
        // high. The cleanup delay must be outside the masked DMAC section too.
        for (unsigned busy=0;busy<3;++busy) {
            reset_spi_start(previous);
            if (busy == 0) REG_DMAC_CHCTRLA.values[DMA_CHANNEL_SPI_TX] = DMA_CHANNEL_ENABLE;
            if (busy == 1) REG_DMAC_BUSYCH = 1U << DMA_CHANNEL_SPI_TX;
            if (busy == 2) REG_DMAC_PENDCH = 1U << DMA_CHANNEL_SPI_TX;
            start_spi_dma_if_ready();
            assert(primask == previous && spi_critical_depth == 0 && spi_critical_entries == 1);
            assert(!SpiTxActive && !SpiTxAwaitingComplete && !spi_cs_low);
            assert(spi_cs_asserts == 1 && spi_cs_deasserts == 1);
            assert(spi_dma_enables == 0 && spi_dma_flag_clears == 0);
            assert(SpiReadyHead == 0 && SpiReadyCount == 1 && SpiReadyFrameIndex[0] == 1);
            assert(SpiPendingFlags == SPI_FLAG_DMA_ERROR);
            track_spi_start = false;
        }

        for (unsigned active : {0U,1U}) {
            for (unsigned ready : {0U,1U}) {
                if (!active && ready) continue;
                reset_spi_start(previous);
                SpiTxActive = active;
                SpiReadyCount = ready;
                start_spi_dma_if_ready();
                assert(primask == previous && spi_critical_entries == 0);
                assert(spi_cs_asserts == 0 && spi_dma_enables == 0);
                assert(SpiTxActive == bool(active) && SpiReadyCount == ready);
                track_spi_start = false;
            }
        }
    }
    primask = 0;
    std::puts("SPI startup: unmasked CRC/SERCOM/CS guard, protected DMA selection, preemption and busy cleanup passed");
}

void reset_spi_finish(unsigned previous, uint8_t head, unsigned ready=2) {
    reset_spi_start(previous);
    track_spi_start = false;
    track_spi_finish = true;
    finish_expects_cs_release = true;
    SpiTxActive = SpiTxAwaitingComplete = true;
    SpiReadyHead = head;
    SpiReadyCount = ready;
    SpiReadyFrameIndex[head] = 1;
    SpiReadyFrameIndex[(head + 1) % SPI_READY_QUEUE_CAPACITY] = 2;
    spi_cs_asserts = 1;
    spi_cs_low = true;
    spi_tx_irq_enabled = SERCOM_INT_TXC;
    spi_tx_irq_enables = spi_dma_disables = 0;
    REG_DMAC_CHID = DMA_CHANNEL_SPI_TX;
    REG_DMAC_CHCTRLA.values[DMA_CHANNEL_SPI_TX] = 0;
    REG_SERCOM1_INTFLAG.value = SERCOM_INT_TXC | SERCOM_INT_RXC;
}

void assert_spi_finished(unsigned previous, uint8_t old_head, unsigned remaining) {
    assert(primask == previous && spi_critical_depth == 0);
    assert(!SpiTxActive && !SpiTxAwaitingComplete && !spi_cs_low);
    assert(SpiReadyHead == (old_head + 1) % SPI_READY_QUEUE_CAPACITY);
    assert(SpiReadyCount == remaining && spi_cs_deasserts == 1);
    assert(spi_critical_entries == 1);
    assert(spi_tx_irq_enabled == 0);
    assert(spi_sercom_interrupt_disables == 1 && spi_sercom_flag_clears == 1 && spi_sercom_reads == 1);
    assert(!(REG_SERCOM1_INTFLAG.value & (SERCOM_INT_TXC | SERCOM_INT_RXC)));
}

void append_ready_frame_after_cs_release() {
    assert(primask == 0 && spi_critical_depth == 0 && !spi_cs_low);
    // ADC may preempt the lower-priority TXC handler after the atomic GPIO
    // release, while the old queue head is still reserved for this transfer.
    assert(SpiTxActive && SpiTxAwaitingComplete && SpiReadyCount == 1);
    const unsigned tail = (SpiReadyHead + SpiReadyCount) % SPI_READY_QUEUE_CAPACITY;
    SpiReadyFrameIndex[tail] = 2;
    ++SpiReadyCount;
    after_spi_cs_release = nullptr;
}

void test_spi_completion_boundary() {
    for (unsigned previous : {0U,1U}) {
        for (uint8_t head=0;head<SPI_READY_QUEUE_CAPACITY;++head) {
            reset_spi_finish(previous, head);
            SpiTxAwaitingComplete = false;
            REG_SERCOM1_INTFLAG.value = SERCOM_INT_RXC;
            spi_tx_irq_enabled = 0;
            // DMA completion means final DATA write, not final SCK edge. It
            // must only arm TXC, with no CS change, queue pop or busy-wait.
            handle_spi_tx_dma_interrupt(DMA_INT_TRANSFER_COMPLETE);
            assert(SpiTxActive && SpiTxAwaitingComplete && spi_cs_low);
            assert(SpiReadyHead == head && SpiReadyCount == 2);
            assert(spi_cs_deasserts == 0 && spi_critical_entries == 0);
            assert(spi_tx_irq_enables == 1 && spi_tx_irq_enabled == SERCOM_INT_TXC);
            assert(spi_sercom_flag_clears == 0 && spi_sercom_reads == 0);
            // Any number of ISR checks before actual TXC leaves the wire and
            // queue unchanged. Only real TXC may finish the transaction.
            for (unsigned delay=0;delay<100;++delay) irq_handler_sercom1();
            assert(spi_cs_low && SpiReadyCount == 2 && spi_cs_deasserts == 0);
            REG_SERCOM1_INTFLAG.value |= SERCOM_INT_TXC;
            irq_handler_sercom1();
            assert_spi_finished(previous, head, 1);
            assert(SpiReadyFrameIndex[SpiReadyHead] == 2 && SpiPendingFlags == 0);
            // A pending duplicate TXC IRQ must not free the following frame.
            finish_expects_cs_release = false;
            REG_SERCOM1_INTFLAG.value = SERCOM_INT_TXC | SERCOM_INT_RXC;
            irq_handler_sercom1();
            assert(SpiReadyCount == 1 && SpiReadyFrameIndex[SpiReadyHead] == 2);
            assert(spi_cs_deasserts == 1 && spi_critical_entries == 1);
            track_spi_finish = false;
        }

        // A spurious/stale TXC while a new DMA transfer is still running
        // may acknowledge flags, but cannot release its CS or queue slot.
        reset_spi_finish(previous, 0);
        SpiTxAwaitingComplete = false;
        finish_expects_cs_release = false;
        irq_handler_sercom1();
        assert(SpiTxActive && !SpiTxAwaitingComplete && spi_cs_low);
        assert(SpiReadyHead == 0 && SpiReadyCount == 2);
        assert(spi_cs_deasserts == 0 && spi_critical_entries == 0);
        track_spi_finish = false;

        // Explicit DMA errors/partial completion abort without waiting for
        // TXC, which need not ever assert if DATA was never written.
        for (uint8_t flags : {uint8_t(DMA_INT_TRANSFER_ERROR),uint8_t(DMA_INT_SUSPEND),uint8_t(0)}) {
            reset_spi_finish(previous, 1);
            SpiTxAwaitingComplete = false;
            REG_SERCOM1_INTFLAG.value = SERCOM_INT_RXC;
            handle_spi_tx_dma_interrupt(flags);
            assert_spi_finished(previous, 1, 1);
            assert(spi_dma_disables == 1 && spi_tx_irq_enables == 0);
            assert(SpiPendingFlags == SPI_FLAG_DMA_ERROR);
            track_spi_finish = false;
        }
    }

    reset_spi_finish(0, 1, 1);
    after_spi_cs_release = append_ready_frame_after_cs_release;
    irq_handler_sercom1();
    assert_spi_finished(0, 1, 1);
    assert(SpiReadyFrameIndex[SpiReadyHead] == 2 && SpiPendingFlags == 0);
    track_spi_finish = false;
    primask = 0;
    std::puts("SPI completion: actual TXC boundary, immediate CS before cleanup, delayed/duplicate IRQs, ADC preemption and DMA aborts passed");
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

int16_t adc_pattern(unsigned scan, unsigned channel) {
    return int16_t((scan * 97 + channel * 613) % 4096) - 2048;
}
unsigned next_dma_scan = 0;
void fill_next_adc_scan() {
    assert(DMAresultIndex < ADC_SCAN_BUFFER_COUNT);
    assert(DMAdescriptor[DMA_CHANNEL_ADC].BTCNT == ADC_CHANNEL_COUNT);
    assert(DMAdescriptor[DMA_CHANNEL_ADC].DSTADDR ==
        uint32_t(uintptr_t(&DMAresults[DMAresultIndex][ADC_CHANNEL_COUNT])));
    for(unsigned channel=0;channel<ADC_CHANNEL_COUNT;++channel)
        DMAresults[DMAresultIndex][channel]=adc_pattern(next_dma_scan,channel);
    ++next_dma_scan;
}
void test_adc_ping_pong() {
    reset_stream();
#ifdef EMPORIAVUE_TARGET_VUE3
    // Bypass UART here: isolate exact ADC scan ordering and buffer ownership.
    VoltageValuesValid=true;
    VoltagePacketGeneration=VoltagePacketConsumedGeneration=0;
    VoltageAgeScans=VoltageUartErrors=VoltageTelegramUpdates=VoltageRejectedTelegrams=0;
    DecodedVoltage[0]=-1234; DecodedVoltage[1]=567; DecodedVoltage[2]=2047;
#endif
    next_dma_scan=0;
    // First scan is already complete. Every rearm immediately fills the NEXT
    // buffer, before capture_spi_scan reads the old buffer in the same ISR.
    for(unsigned channel=0;channel<ADC_CHANNEL_COUNT;++channel)
        DMAresults[0][channel]=adc_pattern(next_dma_scan,channel);
    ++next_dma_scan;
    after_adc_dma_enabled=fill_next_adc_scan;
    uint64_t fingerprint=14695981039346656037ULL;
    unsigned frames=0;
    for(unsigned scan_number=0;scan_number<SPI_RAW_SCAN_COUNT*128;++scan_number) {
        const unsigned frame_index=SpiBuildFrameIndex,scan_index=SpiBuildScanIndex;
        const unsigned completed=DMAresultIndex;
        handle_adc_dma_interrupt(DMA_INT_TRANSFER_COMPLETE);
        assert(DMAresultIndex==(completed+1)%ADC_SCAN_BUFFER_COUNT);
        assert(DMAresultIndex!=completed);
        const auto &scan=SpiFrames[frame_index].scans[scan_index];
        assert(scan.mux_index==scan_number%8);
#ifdef EMPORIAVUE_TARGET_VUE3
        assert(scan.value[0]==-1234 && scan.value[2]==567 && scan.value[4]==2047);
        const unsigned positions[]{1,3,5,6,7};
        for(unsigned channel=0;channel<ADC_CHANNEL_COUNT;++channel)
            assert(scan.value[positions[channel]]==adc_pattern(scan_number,channel));
#else
        for(unsigned channel=0;channel<ADC_CHANNEL_COUNT;++channel)
            assert(scan.value[channel]==adc_pattern(scan_number,channel));
#endif
        while(SpiReadyCount) {
            const auto &frame=SpiFrames[SpiReadyFrameIndex[SpiReadyHead]];
            assert(frame.header.sample_counter==frames*SPI_RAW_SCAN_COUNT);
            assert(frame.header.sequence==frames);
            const auto *bytes=reinterpret_cast<const uint8_t*>(&frame);
            for(unsigned i=0;i<SPI_FRAME_SIZE;++i) fingerprint=(fingerprint^bytes[i])*1099511628211ULL;
            ++frames;
            SpiReadyHead=(SpiReadyHead+1)%SPI_READY_QUEUE_CAPACITY;
            --SpiReadyCount;
        }
    }
    after_adc_dma_enabled=nullptr;
    assert(frames==128 && SpiSampleCounter==SPI_RAW_SCAN_COUNT*128);
    std::printf("ADC scan ordering / full-frame fingerprint: %016llx\n",(unsigned long long)fingerprint);
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
    assert(SpiFrameSequence == 4);
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
    test_sleep_decision();
    test_flash_sleep_configuration();
    test_spi_start_critical_scope();
    test_spi_completion_boundary();
    test_adc_startup();
    test_adc_ping_pong();
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
    crc_table = source[source.index("static const uint32_t Crc32Table[256]"):]
    crc_table = crc_table[:crc_table.index("};") + 2]
    names = [
        "Config_NVMCTRL",
        "wait_for_spi_work",
        "spi_ready_queue_contains", "spi_find_free_build_frame",
        "finalize_spi_frame", "capture_spi_scan",
        "start_spi_dma_if_ready",
        "finish_spi_tx", "irq_handler_sercom1", "handle_spi_tx_dma_interrupt",
    ]
    common = "\n".join([
        "#ifdef EMPORIAVUE_TARGET_VUE3",
        function(source, "write_vue3_voltage_diagnostics"),
        "#endif",
        *(function(source, name) for name in names),
    ])
    cs_release = function(source, "spi_frame_cs_deassert")
    cs_release = re.sub(r"//[^\n]*|/\*.*?\*/", "", cs_release, flags=re.S)
    assert re.sub(r"\s+", " ", cs_release).strip() == (
        "static void spi_frame_cs_deassert(void) { REG_PORT_OUTSET = SPI_FRAME_CS_PIN_MASK; }"
    ), "CS release must be one atomic GPIO write, without a post-transfer delay"
    uart = "\n".join(function(source, name) for name in ["irq_handler_sercom0", "decode_vue3_voltage_packet"])
    adc = "\n".join(function(source, name) for name in ["prepare_adc_scan_start", "enable_adc_dma", "recover_adc_scan", "handle_adc_dma_interrupt"])
    program = "\n".join([
        MOCKS, declarations, descriptors, crc_table, common,
        "#ifdef EMPORIAVUE_TARGET_VUE3", uart, "#endif", adc, TESTS,
    ])
    program = re.sub(r'__asm__ __volatile__\("dmb sy"(?: ::: "memory")?\);', '(void) 0;', program)
    program = program.replace("(uint32_t) &", "(uint32_t) (uintptr_t) &")
    program = program.replace("(uint32_t) bytes", "(uint32_t) (uintptr_t) bytes")
    # Discarding a hardware integer lvalue reads DATA; discarding a C++ proxy
    # object does not invoke its conversion, so make that MMIO read explicit.
    program = program.replace("(void) REG_SERCOM1_DATA;", "(void) uint16_t(REG_SERCOM1_DATA);")
    with tempfile.TemporaryDirectory(prefix="samd09-spi-tests-") as directory:
        for hardware in (2, 3):
            defines = ["-DEMPORIAVUE_TARGET_VUE3=1"] if hardware == 3 else []
            results = []
            assert "#define ADC_SCAN_BUFFER_COUNT 2" in program
            for buffers in (2, 6):
                output = Path(directory) / f"vue{hardware}-{buffers}buffers"
                variant = program.replace("#define ADC_SCAN_BUFFER_COUNT 2", f"#define ADC_SCAN_BUFFER_COUNT {buffers}")
                command = shlex.split(os.environ.get("CXX", "c++")) + [
                    "-std=c++11", "-O2", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=undefined", "-fno-sanitize-recover=all", *defines,
                    "-x", "c++", "-", "-o", str(output),
                ]
                subprocess.run(command, input=variant, text=True, check=True)
                result = subprocess.run([str(output)], text=True, capture_output=True)
                if result.returncode:
                    raise AssertionError(f"{output.name} failed ({result.returncode}):\n{result.stdout}{result.stderr}")
                results.append(result.stdout)
            assert results[0] == results[1], "Two- and six-buffer results differ"
            print(f"Vue {hardware}:", flush=True)
            print(results[0], end="")
            print("Two/six ADC buffers: identical frame bytes and fault-test results")


if __name__ == "__main__":
    main()
