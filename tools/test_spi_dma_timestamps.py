#!/usr/bin/env python3
"""Verify that SPI metering keeps ISR DMA-completion times across RX backlog."""

import re

from test_esphome_metering import HEADER, PRELUDE, SPI, compile_run, component_fields, function


def test_dma_completion_timestamps():
    methods = ["spi_transaction_completed_", "queue_spi_receive_", "handoff_spi_transaction_"]
    bodies = [function(SPI, "EmporiaVueComponent::" + name) for name in methods]
    declarations = [body[:body.index("{")].replace("EmporiaVueComponent::", "").rstrip() + ";"
                    for body in bodies]
    assert "void IRAM_ATTR" in bodies[0]
    assert "post_trans_cb = EmporiaVueComponent::spi_transaction_completed_" in SPI
    assert "frame->received_ms = completed_ms" in bodies[2]
    assert "millis()" not in bodies[2]
    structs = HEADER[HEADER.index("  struct SpiDmaSlot {"):HEADER.index("  enum class SpiFrameValidationError")]
    structs = structs.replace("#endif", "")
    fields = component_fields(*bodies)
    constants = "\n".join(re.findall(r"^static constexpr[^\n]*(?:SPI_RX_QUEUE_SIZE|SPI_RAW_FRAME_SIZE)[^\n]*;",
                                     HEADER, re.M))
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
int main() {
  EmporiaVueComponent c;
  static_assert(sizeof(EmporiaVueComponent::SpiDmaSlot)==8);
  static_assert(sizeof(c.spi_dma_slots_)==128);
  uint8_t buffers[16][1024]{};
  EmporiaVueComponent::SpiQueuedFrame output;
  Queue free, ready; c.spi_processing_free_queue_=&free; c.spi_processing_ready_queue_=&ready;
  c.spi_transaction_completed_(nullptr);
  spi_slave_transaction_t no_context;
  c.spi_transaction_completed_(&no_context);
  assert(queued==0); // ISR callback does no queueing, logging or receive work.
  for (unsigned i=0;i<16;++i) {
    c.spi_rx_buffers_[i]=buffers[i];
    assert(c.queue_spi_receive_(i));
    auto &t=c.spi_transactions_[i];
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
    assert(output.received_ms==100+i*3);
    assert(last_queued==&c.spi_transactions_[i]);
    assert(c.spi_dma_slots_[i].completed_ms==0); // Requeue happens after capture.
  }
  assert(queued==32 && c.spi_rx_received_frames_==16 && c.spi_rx_inflight_==16);
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
  std::puts("PASS SPI DMA timestamps: ISR capture, 16-slot backlog, ownership, millis wrap and full queue");
}
"""
    compile_run(PRELUDE + mocks + constants + "\nclass EmporiaVueComponent {public:\n" +
                structs + fields + "\n".join(declarations) + "\n};\n" + "\n".join(bodies) + tests)


if __name__ == "__main__":
    test_dma_completion_timestamps()
