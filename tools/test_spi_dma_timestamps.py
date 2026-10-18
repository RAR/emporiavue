#!/usr/bin/env python3
"""Test real SPI DMA queueing, buffer headroom, frame validation and timestamps."""

import re

from test_esphome_metering import HEADER, PRELUDE, SPI, compile_run, component_fields, function


def test_receive_capacity_setup():
    # All driver capacities must allow CS to terminate a 1024-byte wire frame.
    # The processing frame and protocol validator deliberately stay at 1024.
    setup = function(SPI, "EmporiaVueComponent::setup_spi_receiver_")
    queue = function(SPI, "EmporiaVueComponent::queue_spi_receive_")
    handoff = function(SPI, "EmporiaVueComponent::handoff_spi_transaction_")
    assert "SPI_RX_BUFFER_SIZE = SPI_RAW_FRAME_SIZE + 4;" in HEADER
    assert "bus_config.max_transfer_sz = SPI_RX_BUFFER_SIZE;" in setup
    assert "heap_caps_malloc(SPI_RX_BUFFER_SIZE, MALLOC_CAP_DMA)" in setup
    assert "].length = SPI_RX_BUFFER_SIZE * 8;" in queue
    assert "max_transfer_sz = SPI_RAW_FRAME_SIZE" not in setup
    assert "heap_caps_malloc(SPI_RAW_FRAME_SIZE," not in setup
    assert "].length = SPI_RAW_FRAME_SIZE * 8" not in queue
    assert "std::memcpy(frame->data, transaction->rx_buffer, SPI_RAW_FRAME_SIZE);" in handoff
    assert "alignas(4) uint8_t data[SPI_RAW_FRAME_SIZE]{};" in HEADER
    print("PASS SPI RX capacity: driver, allocation and transaction share headroom; wire size unchanged")


def test_dma_completion_timestamps():
    methods = ["spi_transaction_completed_", "queue_spi_receive_", "handoff_spi_transaction_",
               "validate_spi_frame_"]
    bodies = [function(SPI, "EmporiaVueComponent::" + name) for name in methods]
    declarations = [body[:body.index("{")].replace("EmporiaVueComponent::", "").rstrip() + ";"
                    for body in bodies]
    assert "void IRAM_ATTR" in bodies[0]
    assert "post_trans_cb = EmporiaVueComponent::spi_transaction_completed_" in SPI
    assert "frame->received_ms = completed_ms" in bodies[2]
    assert "millis()" not in bodies[2]
    structs = HEADER[HEADER.index("  struct SpiDmaSlot {"):HEADER.index("  struct SpiVoltageDiagnostics {")]
    structs = structs.replace("#endif", "")
    fields = component_fields(*bodies)
    constants = "\n".join(re.findall(r"^static constexpr[^\n]*(?:SPI_RX_QUEUE_SIZE|SPI_RAW_FRAME_SIZE|SPI_RX_BUFFER_SIZE)[^\n]*;",
                                     HEADER, re.M))
    helpers = SPI[SPI.index("static constexpr uint8_t SPI_VUE2_RAW_FRAME_VERSION"):
                  SPI.index("void EmporiaVueComponent::publish_spi_diagnostics_")]
    mocks = r"""
#define USE_ESP32
#define IRAM_ATTR
using spi_host_device_t = int;
const int SPI2_HOST=2;
using esp_err_t = int;
const int ESP_OK=0, pdTRUE=1;
struct spi_slave_transaction_t {
  size_t length{0}, trans_len{0}; void *rx_buffer{nullptr}; void *user{nullptr};
};
unsigned queued=0;
spi_slave_transaction_t *last_queued=nullptr;
esp_err_t spi_slave_queue_trans(int,spi_slave_transaction_t *t,int) {
  ++queued; last_queued=t; return ESP_OK;
}
struct Queue {void *item{nullptr}; bool accepts{true};};
using QueueHandle_t = Queue*;
int xQueueReceive(QueueHandle_t q,void *out,unsigned) {
  if (q->item==nullptr) return 0;
  *static_cast<void**>(out)=q->item; q->item=nullptr; return pdTRUE;
}
int xQueueSend(QueueHandle_t q,const void *item,unsigned) {
  if (!q->accepts) return 0;
  q->item=*static_cast<void* const*>(item); return pdTRUE;
}
"""
    tests = r"""
void crc(uint8_t *data) {
  uint32_t value=UINT32_MAX;
  for (unsigned byte=0;byte<SPI_RAW_FRAME_SIZE-4;++byte) {
    value^=data[byte];
    for (unsigned bit=0;bit<8;++bit) value=(value>>1)^((value&1) ? 0xEDB88320U : 0);
  }
  value=~value;
  for (unsigned byte=0;byte<4;++byte) data[SPI_RAW_FRAME_SIZE-4+byte]=value>>(byte*8);
}
int main() {
  EmporiaVueComponent c;
  static_assert(SPI_RAW_FRAME_SIZE==1024 && SPI_RX_BUFFER_SIZE==1028);
  static_assert(SPI_RX_BUFFER_SIZE%4==0);
  static_assert(sizeof(EmporiaVueComponent::SpiDmaSlot)==8);
  static_assert(sizeof(c.spi_dma_slots_)==128);
  uint8_t buffers[SPI_RX_QUEUE_SIZE][SPI_RX_BUFFER_SIZE]{};
  struct GuardedOutput {
    uint32_t before{0x12345678};
    EmporiaVueComponent::SpiQueuedFrame frame;
    uint32_t after[2]{0x89ABCDEF,0x76543210};
  } guarded;
  auto &output=guarded.frame;
  static_assert(sizeof(output.data)==1024);
  auto check_guard=[&]() {
    assert(guarded.before==0x12345678 && guarded.after[0]==0x89ABCDEF && guarded.after[1]==0x76543210);
  };
  Queue free, ready; c.spi_processing_free_queue_=&free; c.spi_processing_ready_queue_=&ready;
  c.spi_transaction_completed_(nullptr);
  spi_slave_transaction_t no_context;
  c.spi_transaction_completed_(&no_context);
  assert(queued==0); // ISR callback does no queueing, logging or receive work.
  for (unsigned i=0;i<16;++i) {
    for (unsigned byte=0;byte<SPI_RAW_FRAME_SIZE;++byte) buffers[i][byte]=i*13+byte;
    for (unsigned byte=SPI_RAW_FRAME_SIZE;byte<SPI_RX_BUFFER_SIZE;++byte) buffers[i][byte]=0xD0+byte%4;
    c.spi_rx_buffers_[i]=buffers[i];
    assert(c.queue_spi_receive_(i));
    auto &t=c.spi_transactions_[i];
    assert(t.length==8224 && t.rx_buffer==buffers[i]);
    assert(t.user==&c.spi_dma_slots_[i] && c.spi_dma_slots_[i].index==i);
    t.trans_len=8192;
    simulated_ms=100+i*3;
    c.spi_transaction_completed_(&t);
    assert(c.spi_dma_slots_[i].completed_ms==100+i*3);
  }
  assert(queued==16 && c.spi_rx_inflight_==16);
  // The RX task is delayed for 1s. Draining its backlog must not compress all
  // sixteen completion timestamps to the retrieval time or reset them early.
  simulated_ms=1100;
  for (unsigned i=0;i<16;++i) {
    free.item=&output; ready.item=nullptr;
    c.handoff_spi_transaction_(&c.spi_transactions_[i]);
    assert(ready.item==&output && output.trans_len_bits==8192);
    assert(std::memcmp(output.data,buffers[i],SPI_RAW_FRAME_SIZE)==0);
    check_guard(); // The spare DMA word must not overwrite the processing frame.
    assert(output.received_ms==100+i*3);
    assert(last_queued==&c.spi_transactions_[i]);
    assert(last_queued->length==8224);
    assert(c.spi_dma_slots_[i].completed_ms==0); // Requeue happens after capture.
  }
  assert(queued==32 && c.spi_rx_received_frames_==16 && c.spi_rx_inflight_==16);
  // Keep the driver's actual bit count, even for short or overlong transfers.
  // Only the fixed wire frame is copied; strict validation happens separately.
  for (size_t bits : {0U,8191U,8192U,8193U,8224U}) {
    auto &t=c.spi_transactions_[0]; t.trans_len=bits;
    free.item=&output; ready.item=nullptr;
    c.handoff_spi_transaction_(&t);
    assert(output.trans_len_bits==bits && ready.item==&output);
    assert(std::memcmp(output.data,buffers[0],SPI_RAW_FRAME_SIZE)==0);
    check_guard();
    assert(last_queued->length==8224);
  }
  assert(queued==37 && c.spi_rx_received_frames_==21 && c.spi_rx_inflight_==16);
  // Timestamp zero is a real completion time, not an 'unset' sentinel.
  for (uint32_t completed : {UINT32_MAX-1,UINT32_MAX,0U,1U}) {
    auto &t=c.spi_transactions_[0]; t.trans_len=8192;
    simulated_ms=completed; c.spi_transaction_completed_(&t);
    simulated_ms=completed+100; free.item=&output;
    c.handoff_spi_transaction_(&t);
    assert(output.received_ms==completed);
  }
  // Full processing queue still immediately returns the DMA slot to the driver.
  auto &t=c.spi_transactions_[7]; t.trans_len=8192;
  simulated_ms=2000; c.spi_transaction_completed_(&t);
  simulated_ms=3000; free.item=nullptr;
  const auto before=queued;
  c.handoff_spi_transaction_(&t);
  assert(queued==before+1 && c.spi_processing_overruns_==1 && c.spi_dma_slots_[7].completed_ms==0);
  assert(!c.spi_rx_recover_requested_);
  // Run the production parser for both formats. Invalid lengths must return
  // before even looking at the frame pointer, including the full DMA capacity.
  using Error=EmporiaVueComponent::SpiFrameValidationError;
  for (uint16_t hardware : {2,3}) {
    c.hardware_id_=hardware;
    uint8_t data[SPI_RAW_FRAME_SIZE]{};
    data[0]=data[1]=hardware==3 ? 2 : 1;
    data[2]=0xF0; data[3]=3;
    data[4]=0x34; data[5]=0x12;
    data[8]=0x12; data[9]=0x34; data[10]=0x56; data[11]=0x78;
    if (hardware==3) {
      data[6]=(816U<<3)&255; data[7]=(816U<<3)>>8;
    } else {
      data[12+17]=632&255; data[12+18+17]=632>>8;
    }
    crc(data);
    auto parsed=c.validate_spi_frame_(data,8192);
    assert(parsed.error==Error::NONE && parsed.sequence==0x1234 && parsed.sample_counter==0x78563412);
    assert(parsed.sample_period_ticks==(hardware==3 ? 816 : 632));
    for (uint16_t bits : {0,8191,8193,8224}) {
      auto rejected=c.validate_spi_frame_(nullptr,bits);
      assert(rejected.error==Error::TRANSFER_LENGTH && rejected.transfer_length_bits==bits);
      assert(c.validate_spi_frame_(data,bits).error==Error::TRANSFER_LENGTH);
    }
    data[100]^=1;
    assert(c.validate_spi_frame_(data,8192).error==Error::CRC_MISMATCH);
  }
  std::puts("PASS SPI DMA: 1028-byte capacity, guarded 1024-byte copy, strict real parser, ISR timestamps and ownership");
}
"""
    compile_run(PRELUDE + mocks + constants + helpers + "\nclass EmporiaVueComponent {public:\n" +
                structs + fields + "\n".join(declarations) + "\n};\n" + "\n".join(bodies) + tests)


if __name__ == "__main__":
    test_receive_capacity_setup()
    test_dma_completion_timestamps()
