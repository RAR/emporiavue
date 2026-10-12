#!/usr/bin/env python3
"""Host regression tests; run with an ESPHome Python environment and a C++ compiler.

Compile the production metering methods, mocking only ESPHome/FreeRTOS I/O.
No device, network access, or generated repository firmware headers are needed.
"""

from pathlib import Path
import importlib.util
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HEADER = (ROOT / "components/emporiavue/emporiavue.h").read_text()
SPI = (ROOT / "components/emporiavue/spi_transport.cpp").read_text()
METERING = (ROOT / "components/emporiavue/metering.cpp").read_text()


def function(source, name):
    match = re.search(r"^(?:[\w:]+\s+)+" + re.escape(name) + r"\([^;]*?\)(?: const)? \{", source, re.M)
    assert match, name
    end, depth = match.end(), 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[match.start():end]


def compile_run(program):
    with tempfile.TemporaryDirectory(prefix="emporiavue-metering-") as folder:
        binary = str(Path(folder) / "test")
        subprocess.run(
            ["c++", "-std=c++17", "-O1", "-fsanitize=undefined", "-fno-sanitize-recover=all",
             "-x", "c++", "-", "-o", binary], input=program, text=True, check=True,
        )
        subprocess.run([binary], check=True)


def component_fields(*bodies):
    """Keep host fixtures in sync with the production component's member types."""
    members = sorted(set(re.findall(r"this->(\w+_)(?!\w|\()", "\n".join(bodies))))
    fields = []
    for name in members:
        match = re.search(r"^  [A-Za-z_][^\n{}]*\b" + name + r"\b[^\n]*;", HEADER, re.M)
        assert match, name
        fields.append(match.group())
    return "\n".join(fields)


PRELUDE = r"""
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cinttypes>
#include <cstring>
#include <limits>
#include <memory>
#include <vector>
#include <cstdio>
#include <cassert>
#include <string>
#include <functional>
#define ESP_LOGD(...) ((void)0)
#define ESP_LOGI(...) ((void)0)
#define ESP_LOGW(...) ((void)0)
#define ESP_LOGV(...) ((void)0)
uint32_t simulated_ms = 0;
uint32_t millis() { return simulated_ms; }
enum class MeteringTransport : uint8_t { UNKNOWN, SPI, I2C };
"""


def test_spi_windows():
    methods = ["reset_spi_metering_state_", "sanitize_spi_adc_offset_", "scale_spi_rms_", "scale_spi_power_",
               "spi_metering_target_samples_", "spi_metering_target_periods_", "spi_crossing_difference_",
               "decode_spi_raw_frame_", "process_spi_raw_scan_", "finish_spi_metering_window_"]
    bodies = [function(SPI, "EmporiaVueComponent::" + name) for name in methods]
    declarations = [body[:body.index("{")].replace("EmporiaVueComponent::", "").rstrip() + ";" for body in bodies]
    reset_marker = "  this->spi_metering_accumulator_ = SpiMeteringAccumulator{};\n}"
    assert bodies[-1].endswith(reset_marker)
    bodies[-1] = bodies[-1][:-len(reset_marker)] + (
        "assert(frame.duration_ms > 0 && std::isfinite(frame.duration_ms));\n"
        "output.push_back(frame);\ncounts.push_back(acc.sample_count);\n" + reset_marker)
    structs = HEADER[HEADER.index("  struct MeteringPhase {"):HEADER.index("  enum MemSize")]
    fields = HEADER[HEADER.index("  SpiMeteringAccumulator spi_metering_accumulator_"):HEADER.index("  volatile uint16_t spi_rx_inflight_")]
    constants = HEADER[HEADER.index("static constexpr float VUE2_STOCK_CYCLE"):HEADER.index("class MeteringPhaseConfig;")]
    helpers = SPI[SPI.index("static constexpr uint8_t SPI_VUE2_RAW_FRAME_VERSION"):SPI.index("void EmporiaVueComponent::publish_spi_diagnostics_")]
    mocks = r"""
struct MeteringPhaseConfig { uint8_t input; uint8_t get_input_wire() const {return input;} };
struct MeteringCTClampConfig {
  uint8_t get_input_port() const {return 0;}
  const MeteringPhaseConfig* get_phase() const {return nullptr;}
  const MeteringPhaseConfig* get_line_pair_phase_b() const {return nullptr;}
  bool is_line_pair() const {return false;}
};
struct VirtualLine {
  const MeteringPhaseConfig* get_line_a() const {return nullptr;}
  const MeteringPhaseConfig* get_line_b() const {return nullptr;}
};
"""
    extra = r"""
  uint16_t hardware_id_{2};
  uint32_t metering_interval_ms_{220};
  float spi_sample_rate_hz_{0};
  uint32_t spi_last_frame_samples_{0}, spi_invalid_window_last_log_ms_{0};
  std::vector<MeteringPhaseConfig*> metering_phases_;
  std::vector<MeteringCTClampConfig*> metering_ct_clamps_;
  std::vector<VirtualLine*> metering_virtual_lines_;
  std::vector<MeteringFrame> output;
  std::vector<uint32_t> counts;
  void push_spi_fundamental_sample_(const SpiRawScan&,const SpiRawScan&,const SpiRawScan&) {}
  bool accumulate_spi_voltage_cycle_(const SpiCrossingPosition&,const SpiCrossingPosition&) {return false;}
"""
    tests = r"""
int main() {
  for (uint16_t hw : {2,3}) for (uint32_t interval : {220U,513U,UINT32_MAX}) {
    EmporiaVueComponent c;
    c.hardware_id_ = hw;
    c.metering_interval_ms_ = interval;
    c.spi_main_current_delay_ = c.spi_mux_current_delay_ = 0;
    MeteringPhaseConfig phases[3]{{0},{1},{2}};
    for (auto &p: phases) c.metering_phases_.push_back(&p);
    for (auto &mask : c.spi_power_voltage_mask_) mask = 7;
    c.spi_current_peak_mask_=7;
    const float rate = 16000000.f/(hw == 2 ? 632.f : 816.f);
    uint32_t counter = 0, sequence = 0;
    bool narrow_pulses = false;
    auto feed = [&](float seconds, bool drop_reference) {
      for (unsigned f = 0; f < static_cast<unsigned>(seconds*rate/56); ++f) {
        uint8_t frame[1024]{};
        for (unsigned s=0;s<56;++s) {
          auto data = frame + 12 + s*18;
          for (unsigned p=0;p<3;++p) {
            double angle = (counter+s)*2.*3.141592653589793*50/rate-p*2.*3.141592653589793/3.;
            int16_t v = drop_reference && p==0 ? 0 : std::lround(1000.*std::sin(angle));
            int16_t i = std::lround(-200.*std::sin(angle));
            if (narrow_pulses && (counter+s)%1000==0) i=2000;
            if (narrow_pulses && (counter+s)%1000==500) i=-2000;
            data[p*4]=v&255; data[p*4+1]=(v>>8)&255;
            data[p*4+2]=i&255; data[p*4+3]=(i>>8)&255;
          }
          data[16]=(counter+s)%8;
        }
        simulated_ms = counter*1000./rate;
        c.spi_sample_rate_hz_=rate;
        c.decode_spi_raw_frame_(frame,sequence++,0,counter);
        assert(c.spi_metering_accumulator_.sample_count < SPI_MAX_WINDOW_SAMPLES);
        counter+=56;
      }
    };
    feed(2.8,false);
    assert(!c.output.empty());
    if (interval == UINT32_MAX) assert(c.spi_metering_target_samples_() == SPI_MAX_METERING_SAMPLES);
    const auto normal = c.output.back().phases[1].voltage_raw;
    assert(std::abs(int(normal)-7070)<5);
    assert(c.output.back().clamps[1].current_peak_valid);
    assert(std::abs(int(c.output.back().clamps[1].current_peak_raw)-2000)<10);
    for (int repeat=0;repeat<3;++repeat) {
      auto before = c.output.size();
      feed(4.0,true); // Raw packets continue normally; only reference crossings disappear.
      assert(c.output.size()==before);
      feed(1.6,false);
      assert(c.output.size()>before);
      for (auto n=before;n<c.output.size();++n) {
        assert(c.output[n].valid && c.counts[n]<SPI_MAX_WINDOW_SAMPLES);
        assert(std::abs(int(c.output[n].phases[1].voltage_raw)-int(normal))<10);
      }
    }
    narrow_pulses=true;
    feed(2.8,false);
    // The complete decoding/metering path must retain isolated samples too.
    assert(c.output.back().clamps[1].current_peak_valid);
    assert(c.output.back().clamps[1].current_peak_raw>19000);
    std::printf("PASS Vue %u SPI: bounded windows and clean recovery (interval=%u)\n",hw,interval);
  }
}
"""
    compile_run(PRELUDE + mocks + constants + helpers + "\nclass EmporiaVueComponent {public:\n" +
                structs + fields + extra + "\n".join(declarations) + "\n};\n" + "\n".join(bodies) + tests)


def test_spi_error_classification():
    body = function(SPI, "EmporiaVueComponent::process_spi_frame_")
    structs = HEADER[HEADER.index("  struct SpiQueuedFrame {"):HEADER.index("  struct SpiFundamentalSample {")]
    structs = structs.replace("#endif", "")
    fields = component_fields(body)
    constants = "\n".join(re.findall(r"^static constexpr[^\n]*;", SPI, re.M))
    size = re.search(r"^static constexpr uint16_t SPI_RAW_FRAME_SIZE[^\n]*;", HEADER, re.M).group()
    mocks = r"""
using portMUX_TYPE = int;
#define portMUX_INITIALIZER_UNLOCKED 0
#define portENTER_CRITICAL(...) ((void)0)
#define portEXIT_CRITICAL(...) ((void)0)
"""
    methods = r"""
  SpiFrameValidationResult next;
  unsigned decoded{0}, resets{0};
  SpiFrameValidationResult validate_spi_frame_(const uint8_t*, uint16_t) {return next;}
  void decode_spi_raw_frame_(const uint8_t*, uint32_t, uint32_t, uint32_t) {++decoded;}
  void reset_spi_metering_state_() {++resets;}
  SpiVoltageDiagnostics decode_spi_voltage_diagnostics_(const uint8_t*, const SpiFrameValidationResult&, uint16_t) {
    return {};
  }
  void process_spi_frame_(const SpiQueuedFrame&);
"""
    tests = r"""
int main() {
  using Error = EmporiaVueComponent::SpiFrameValidationError;
  EmporiaVueComponent::SpiQueuedFrame frame;
  for (uint32_t flags : {0U,1U,2U,4U,6U,0x8000U,0x8007U}) {
    EmporiaVueComponent c;
    c.next.flags=flags; c.next.sample_period_ticks=816;
    c.process_spi_frame_(frame);
    const bool invalid = (flags & 0x8006) != 0;
    assert(c.decoded == !invalid && c.resets == invalid);
    assert(c.spi_rx_valid_frames_ == !invalid);
    assert(c.spi_rx_voltage_errors_ == bool(flags & 4));
    assert(c.spi_rx_dma_errors_ == bool(flags & 2));
    assert(c.spi_rx_adc_overruns_ == bool(flags & 0x8000));
    assert(c.spi_rx_samd_overruns_ == bool(flags & 1));
    assert(c.spi_rx_crc_errors_ == 0 && c.spi_rx_sync_errors_ == 0);
    // No stale-frame grace period: genuine voltage faults still reset metering.
    c.next.flags=0; c.next.sequence=1; c.process_spi_frame_(frame);
    assert(c.decoded == 1U + !invalid && c.spi_rx_invalid_streak_ == 0);
    assert(c.spi_rx_valid_frames_ == 1U + !invalid);
  }
  for (auto error : {Error::TRANSFER_LENGTH,Error::HEADER,Error::PAYLOAD_LENGTH,
                     Error::CRC_MISMATCH,Error::SAMPLE_PERIOD}) {
    EmporiaVueComponent c;
    c.next.flags=0x8007; c.next.error=error;
    c.process_spi_frame_(frame);
    // Never interpret corrupt frame flags as real SAMD acquisition faults.
    assert(c.spi_rx_voltage_errors_ == 0 && c.spi_rx_dma_errors_ == 0);
    assert(c.spi_rx_adc_overruns_ == 0 && c.spi_rx_samd_overruns_ == 0);
    assert(c.spi_rx_sync_errors_ == 1 && c.decoded == 0);
    assert(c.spi_rx_valid_frames_ == 0);
  }
  std::puts("PASS SPI: separate voltage/DMA errors, strict rejection and valid recovery");
}
"""
    compile_run(PRELUDE + mocks + size + constants + "\nclass EmporiaVueComponent {public:\n" +
                structs + fields + methods + "};\n" + body + tests)


def test_spi_status_logging():
    status = function(SPI, "EmporiaVueComponent::log_spi_receiver_status_")
    handoff = function(SPI, "EmporiaVueComponent::handoff_spi_transaction_")
    restart = function(SPI, "EmporiaVueComponent::restart_spi_receiver_")
    assert restart.index("this->log_spi_receiver_status_(true)") < restart.index("this->stop_spi_receiver_()")
    # Neither diagnostic total may be erased by soft recovery or a SAMD reset.
    assert "spi_rx_received_frames_ =" not in restart and "spi_rx_valid_frames_ =" not in restart
    assert "spi_metering_window_drops_ =" not in restart and "spi_metering_stale_windows_ =" not in restart
    setup = function(SPI, "EmporiaVueComponent::setup_spi_receiver_")
    for counter in ("spi_metering_window_drops_", "spi_metering_stale_windows_"):
        assignment = f"this->{counter} = 0;"
        assert setup.count(assignment) == 1
        assert setup.index("if (reset_statistics) {") < setup.index(assignment) < setup.index("this->spi_rx_last_flags_ = 0;")
    assert "metering_journal=%u" in setup
    fields = component_fields(status, handoff)
    frame = HEADER[HEADER.index("  struct SpiDmaSlot {"):HEADER.index("  enum class SpiFrameValidationError")]
    frame = frame.replace("#endif", "")
    voltage_struct = HEADER[HEADER.index("  struct SpiVoltageDiagnostics {"):
                            HEADER.index("  struct SpiFundamentalSample {")]
    constants = "\n".join(re.findall(
        r"^[ \t]*static constexpr[^\n]*(?:SPI_RAW_FRAME_SIZE|METERING_STATUS_LOG_INTERVAL_MS)[^\n]*;", HEADER, re.M))
    mocks = r"""
#include <cstdarg>
#define USE_ESP32
std::vector<std::string> messages;
void log_capture(const char *format, ...) __attribute__((format(printf,1,2)));
void log_capture(const char *format, ...) {
  char text[1024]; va_list args; va_start(args,format);
  const int length=vsnprintf(text,sizeof(text),format,args); va_end(args);
  assert(length>=0 && length<int(sizeof(text))); messages.emplace_back(text);
}
#undef ESP_LOGD
#define ESP_LOGD(tag, ...) log_capture(__VA_ARGS__)
struct Queue {void *item{nullptr}; bool accepts{true}; unsigned pending{0};};
using QueueHandle_t = Queue*;
using UBaseType_t = unsigned;
const int pdTRUE=1;
unsigned uxQueueMessagesWaiting(QueueHandle_t q) {return q->pending;}
int xQueueReceive(QueueHandle_t q, void *out, unsigned) {
  if (!q->item) return 0;
  *static_cast<void**>(out)=q->item; q->item=nullptr; return pdTRUE;
}
int xQueueSend(QueueHandle_t q, const void *in, unsigned) {
  if (!q->accepts) return 0;
  q->item=*static_cast<void* const*>(in); return pdTRUE;
}
struct spi_slave_transaction_t {void *user; size_t trans_len; const void *rx_buffer;};
"""
    methods = r"""
  unsigned requeued{0};
  SpiVoltageDiagnostics voltage;
  SpiVoltageDiagnostics get_spi_voltage_diagnostics_() {return voltage;}
  bool queue_spi_receive_(uint8_t index) {assert(index==0); ++requeued; return true;}
  void handoff_spi_transaction_(spi_slave_transaction_t*);
  void log_spi_receiver_status_(bool force=false);
"""
    tests = r"""
int main() {
  EmporiaVueComponent c;
  Queue free, ready;
  c.spi_processing_free_queue_=&free; c.spi_processing_ready_queue_=&ready;
  EmporiaVueComponent::SpiQueuedFrame output;
  uint8_t bytes[SPI_RAW_FRAME_SIZE]{};
  EmporiaVueComponent::SpiDmaSlot slot; slot.completed_ms=123; slot.index=0;
  spi_slave_transaction_t transaction{&slot,0,bytes};
  c.handoff_spi_transaction_(nullptr); assert(c.spi_rx_received_frames_==0);
  free.item=&output; c.handoff_spi_transaction_(&transaction);
  assert(c.spi_rx_received_frames_==1 && output.trans_len_bits==0);
  assert(output.received_ms==123);
  transaction.trans_len=8192;
  c.handoff_spi_transaction_(&transaction); // Queue exhausted, still a received transfer.
  assert(c.spi_rx_received_frames_==2 && c.spi_processing_overruns_==1);
  free.item=&output; ready.accepts=false; c.handoff_spi_transaction_(&transaction);
  assert(c.spi_rx_received_frames_==3 && c.spi_processing_overruns_==2 && c.requeued==3);
  c.spi_rx_valid_frames_=7;
  c.spi_rx_received_frames_=10;
  c.spi_rx_last_log_ms_=1000; simulated_ms=3000;
  c.log_spi_receiver_status_(); assert(messages.empty());
  c.log_spi_receiver_status_(true); assert(messages.size()==1);
  assert(messages.back().find("received_frames=10 valid_frames=7")!=std::string::npos);
  assert(messages.back().find("processing_overruns=2")!=std::string::npos);
  // Repeated two-second recovery, with no counter changes, still emits a snapshot.
  for (unsigned i=0;i<6;++i) {
    simulated_ms+=2000; c.spi_rx_last_log_ms_=simulated_ms-2000;
    c.log_spi_receiver_status_(true); assert(messages.size()==i+2);
  }
  // Healthy progress is quiet. Ordinary error logging remains throttled.
  simulated_ms+=10000; ++c.spi_rx_received_frames_; ++c.spi_rx_valid_frames_;
  c.log_spi_receiver_status_(); assert(messages.size()==7);
  ++c.spi_rx_voltage_errors_; c.log_spi_receiver_status_(); assert(messages.size()==8);
  simulated_ms+=1; ++c.spi_rx_voltage_errors_;
  c.log_spi_receiver_status_(); assert(messages.size()==8);
  simulated_ms+=10000; c.log_spi_receiver_status_(); assert(messages.size()==9);
  assert(messages.back().find("received_frames=11 valid_frames=8")!=std::string::npos);
  assert(messages.back().find("voltage_errors=2")!=std::string::npos);
  c.spi_processing_ready_queue_=nullptr; c.log_spi_receiver_status_(true);
  assert(messages.back().find("processing_pending=0")!=std::string::npos);
  c.voltage.available=true; c.voltage.voltage_valid=true;
  c.voltage.accepted_telegrams=123; c.voltage.uart_errors=4;
  c.voltage.rejected_telegrams=5; c.voltage.age_scans=10; c.voltage.sample_period_ticks=816;
  c.log_spi_receiver_status_(true);
  assert(messages.back().find("accepted=123 uart_errors=4 rejected=5 age_ms=0.5")!=std::string::npos);
  messages.clear(); simulated_ms+=10000; ++c.voltage.accepted_telegrams;
  c.log_spi_receiver_status_(); assert(messages.empty()); // Normal UART progress remains quiet.
  ++c.voltage.uart_errors; c.log_spi_receiver_status_(); assert(messages.size()==2);
  assert(messages.back().find("uart_errors=5")!=std::string::npos);
  ++c.voltage.rejected_telegrams; c.log_spi_receiver_status_(); assert(messages.size()==2);
  simulated_ms+=10000; c.log_spi_receiver_status_(); assert(messages.size()==4);
  messages.clear(); simulated_ms+=10000;
  const auto transfer_errors=c.spi_rx_queue_errors_+c.spi_rx_dma_errors_;
  c.spi_metering_window_drops_=2; c.log_spi_receiver_status_(); assert(messages.size()==1);
  assert(messages.back().find("metering_window_drops=2 metering_stale_windows=0")!=std::string::npos);
  simulated_ms+=10000; c.spi_metering_stale_windows_=3; c.log_spi_receiver_status_();
  assert(messages.size()==2);
  assert(messages.back().find("metering_window_drops=2 metering_stale_windows=3")!=std::string::npos);
  assert(c.spi_rx_queue_errors_+c.spi_rx_dma_errors_==transfer_errors);
  std::puts("PASS SPI status: RX/drop counters, forced recovery snapshots, unchanged/healthy throttling");
}
"""
    compile_run(PRELUDE + mocks + constants + "\nclass EmporiaVueComponent {public:\n" +
                frame + voltage_struct + fields + methods + "};\n" + status + handoff + tests)


def test_current_peak_preservation():
    start = SPI.index("static void update_current_extrema")
    end = SPI.index("void EmporiaVueComponent::publish_spi_diagnostics_", start)
    helpers = SPI[start:end]
    accumulator = r"""
struct Accumulator {
  int16_t current_min_raw[19]{};
  int16_t current_max_raw[19]{};
  bool current_extrema_valid[19]{};
};
"""
    tests = r"""
int main() {
  Accumulator acc;
  for (unsigned sample=0; sample<100; ++sample) {
    const float angle=sample*2.f*3.14159265358979323846f/100.f;
    const int16_t value=std::lround(200.f*std::sin(angle));
    update_current_extrema(acc.current_min_raw,acc.current_max_raw,acc.current_extrema_valid,0,value);
  }
  assert(acc.current_extrema_valid[0]);
  assert(acc.current_max_raw[0]==200);
  assert(acc.current_min_raw[0]==-200);
  assert(!acc.current_extrema_valid[1]);

  // One- and two-sample peaks must survive, independent of channel, polarity,
  // offset and position in the metering window (including its boundaries).
  for (uint8_t channel : {0,2,3,18}) for (int polarity : {-1,1})
      for (int width : {1,2,3}) for (int position : {0,41,97}) {
    Accumulator pulse;
    for (int sample=0;sample<100;sample++) {
      const int16_t value=123+(sample>=position && sample<position+width ? polarity*2000 : 0);
      update_current_extrema(pulse.current_min_raw,pulse.current_max_raw,pulse.current_extrema_valid,channel,value);
    }
    assert(pulse.current_extrema_valid[channel]);
    assert(pulse.current_max_raw[channel]==(polarity>0 ? 2123 : 123));
    assert(pulse.current_min_raw[channel]==(polarity<0 ? -1877 : 123));
  }
  Accumulator limits;
  for (int16_t value : {INT16_MIN,INT16_MAX})
    update_current_extrema(limits.current_min_raw,limits.current_max_raw,limits.current_extrema_valid,0,value);
  assert(limits.current_min_raw[0]==INT16_MIN && limits.current_max_raw[0]==INT16_MAX);
  limits=Accumulator{};
  assert(!limits.current_extrema_valid[0]);
  std::puts("PASS current peak: sine, narrow pulses, polarity, offsets, window edges and ADC limits");
}
"""
    compile_run(PRELUDE + helpers + accumulator + tests)


def test_fundamental_analysis_math():
    body = function(METERING, "EmporiaVueComponent::calculate_ct_fundamental_analysis_")
    declaration = body[:body.index("{")].replace("EmporiaVueComponent::", "").rstrip() + ";"
    mocks = r"""
namespace sensor {struct Sensor {};}
struct MeteringFrame {MeteringTransport transport{MeteringTransport::SPI};};
struct MeteringCTMeasurement {
  bool has_current{false}; float current{0}; bool has_fundamental_analysis{false};
  float fundamental_current{0}, fundamental_reactive_power{0};
  float fundamental_active_power{0}, fundamental_voltage{0};
  float fundamental_power_factor{NAN}, displacement_angle{NAN}, current_thd{NAN};
};
struct MeteringCTClampConfig {
  uint32_t get_analysis_interval() const {return 0;}
  bool has_fundamental_power_analysis() const {return true;}
  sensor::Sensor reactive, factor, angle, thd;
  bool want_reactive{true}, want_factor{true}, want_angle{true}, want_thd{true};
  sensor::Sensor *get_fundamental_reactive_power_sensor() const {return want_reactive ? const_cast<sensor::Sensor*>(&reactive) : nullptr;}
  sensor::Sensor *get_fundamental_power_factor_sensor() const {return want_factor ? const_cast<sensor::Sensor*>(&factor) : nullptr;}
  sensor::Sensor *get_displacement_angle_sensor() const {return want_angle ? const_cast<sensor::Sensor*>(&angle) : nullptr;}
  sensor::Sensor *get_current_thd_sensor() const {return want_thd ? const_cast<sensor::Sensor*>(&thd) : nullptr;}
};
class EmporiaVueComponent {public:
  float minimum_fundamental_current_{0.02f};
  float vi{230}, vq{0}, ci{0}, cq{0}; bool phasors_valid{true};
  bool calculate_ct_fundamental_phasors_(const MeteringFrame&,const MeteringCTClampConfig*,float *out_vi,
                                         float *out_vq,float *out_ci,float *out_cq,bool) const {
    if (!phasors_valid) return false;
    *out_vi=vi; *out_vq=vq; *out_ci=ci; *out_cq=cq; return true;
  }
""" + declaration + "\n};\n"
    tests = r"""
int main() {
  EmporiaVueComponent c; MeteringFrame frame; MeteringCTClampConfig ct; MeteringCTMeasurement m;
  const float angle=30.f*3.14159265358979323846f/180.f;
  c.ci=2.f*std::cos(angle); c.cq=2.f*std::sin(angle);
  m.has_current=true; m.current=2.5f;
  assert(c.calculate_ct_fundamental_analysis_(frame,&ct,&m));
  assert(std::fabs(m.fundamental_current-2.f)<1e-5f);
  assert(std::fabs(m.fundamental_reactive_power-230.f)<1e-3f);
  assert(std::fabs(m.fundamental_power_factor-std::cos(angle))<1e-5f);
  assert(std::fabs(m.displacement_angle-30.f)<1e-4f);
  assert(std::fabs(m.current_thd-75.f)<1e-4f);

  c.ci=0.01f; c.cq=0; m=MeteringCTMeasurement{}; m.has_current=true; m.current=1.f;
  assert(c.calculate_ct_fundamental_analysis_(frame,&ct,&m));
  assert(m.fundamental_current==0 && m.fundamental_reactive_power==0);
  assert(std::isnan(m.fundamental_power_factor) && std::isnan(m.displacement_angle) && std::isnan(m.current_thd));

  c.ci=3.f; m=MeteringCTMeasurement{}; m.has_current=true; m.current=2.f;
  assert(c.calculate_ct_fundamental_analysis_(frame,&ct,&m));
  assert(std::isnan(m.current_thd));
  frame.transport=MeteringTransport::I2C;
  assert(!c.calculate_ct_fundamental_analysis_(frame,&ct,&m));
  std::puts("PASS fundamental analysis: RMS magnitude, Q1, PF1, displacement, THD and validity");
}
"""
    compile_run(PRELUDE + mocks + body + tests)


def test_energy_gaps():
    methods = ["setup", "dump_config", "publish_state_and_save", "check_day_", "add_integral_wh",
               "interval_duration_today_ms_", "interval_energy_wh",
               "schedule_midnight_reset_", "process_metering_state_"]
    bodies = "\n".join(function(METERING, "MeteringDailyEnergy::" + name) for name in methods)
    energy_class = HEADER[HEADER.index("enum class MeteringEnergyMethod"):HEADER.index("class MeteringPowerFilters")]
    energy_class = energy_class.replace("protected:", "public:").replace("time::", "mock_time::")
    mocks = r"""
#include <map>
#include <sys/time.h>
#define LOG_SENSOR(...) ((void)0)
time_t simulated_wall_seconds=1;
long simulated_wall_microseconds=0;
int mock_gettimeofday(struct timeval *out, void *) {
  out->tv_sec=simulated_wall_seconds; out->tv_usec=simulated_wall_microseconds; return 0;
}
#define gettimeofday mock_gettimeofday
struct Application { uint32_t get_loop_component_start_time() {return simulated_ms;} } App;
std::map<uint32_t,std::vector<uint8_t>> preference_data;
struct ESPPreferenceObject {
  uint32_t key{0}; unsigned saves{0}, loads{0};
  template<typename T> bool load(T *out) {
    ++loads; auto it=preference_data.find(key);
    if(it==preference_data.end() || it->second.size()!=sizeof(T)) return false;
    std::memcpy(out,it->second.data(),sizeof(T)); return true;
  }
  template<typename T> bool save(const T *in) {
    ++saves; auto &bytes=preference_data[key]; bytes.resize(sizeof(T));
    std::memcpy(bytes.data(),in,sizeof(T)); return true;
  }
};
struct Preferences {
  template<typename T> ESPPreferenceObject make_preference(uint32_t key) {return {key};}
} preferences;
Preferences *global_preferences=&preferences;
struct Component {
  virtual void setup() {}
  virtual void dump_config() {}
  uint32_t timeout_ms{0}; std::function<void()> timeout;
  void set_timeout(uint32_t id, uint32_t ms, std::function<void()> fn) {assert(id==1); timeout_ms=ms; timeout=fn;}
};
namespace sensor {struct Sensor {
  float state{NAN}; unsigned callbacks{0}; std::function<void(float)> callback;
  void publish_state(float value) {state=value;}
  void add_on_state_callback(std::function<void(float)> fn) {++callbacks; callback=fn;}
};}
struct ESPTime {
  bool valid{false}; unsigned year{2026}, day_of_year{1}, hour{0}, minute{0}, second{0};
  time_t timestamp{1};
  bool is_valid() const {return valid;}
};
namespace mock_time {
struct RealTimeClock {
  ESPTime state; std::function<void()> callback;
  ESPTime now() {return state;}
  void add_on_time_sync_callback(std::function<void()> fn) {callback=fn;}
};
}
"""
    tests = r"""
int main() {
  for (auto method : {MeteringEnergyMethod::LEFT,MeteringEnergyMethod::RIGHT,MeteringEnergyMethod::TRAPEZOID}) {
    preference_data.clear();
    MeteringDailyEnergy::RestoreState restored{};
    restored.day_key=2026001; restored.energy_wh=123;
    auto pref=global_preferences->make_preference<MeteringDailyEnergy::RestoreState>(101);
    pref.save(&restored);
    MeteringDailyEnergy e;
    mock_time::RealTimeClock clock; sensor::Sensor parent;
    e.set_method(method); e.set_parent(&parent); e.set_time(&clock);
    e.set_preference_key(101);
    e.set_energy_scale(1.0f);
    simulated_ms=10000;
    e.setup();
    assert(parent.callbacks==1 && e.pref_.loads==1 && e.state==123 && e.timeout_ms==0);
    parent.callback(3600);
    assert(e.total_energy_==123); // Do not count startup time, including right/trapezoid modes.
    simulated_ms+=1000;
    e.process_metering_state_(3600);
    assert(std::abs(e.total_energy_-124)<0.001);
    // No timeout callback during a stalled loop: the energy guard must still work.
    simulated_ms+=600000;
    e.process_metering_state_(3600);
    assert(std::abs(e.total_energy_-124)<0.001);
    simulated_ms+=1000;
    e.process_metering_state_(3600);
    assert(std::abs(e.total_energy_-125)<0.001);
    for (float invalid : {NAN,INFINITY,-INFINITY}) {
      e.process_metering_state_(invalid);
      simulated_ms+=500;
      e.process_metering_state_(3600);
      assert(std::abs(e.total_energy_-125)<0.001);
    }
    // millis() wrap is a normal short interval, not a 49-day integration gap.
    simulated_ms=UINT32_MAX-500;
    e.process_metering_state_(3600);
    simulated_ms+=1000;
    e.process_metering_state_(3600);
    assert(std::abs(e.total_energy_-126)<0.001);
    simulated_ms+=1000;
    e.process_metering_state_(-3600);
    const float change = method==MeteringEnergyMethod::LEFT ? 1 : method==MeteringEnergyMethod::RIGHT ? -1 : 0;
    assert(std::abs(e.total_energy_-(126+change))<0.001);
    assert(e.pref_.load(&restored) && restored.energy_wh==e.total_energy_);
    clock.state.valid=true; clock.callback();
    assert(e.timeout_ms==81000000 && e.total_energy_>0); // First clock sync retains restored total.
    clock.state.hour=23; clock.state.minute=59; clock.state.second=59; clock.callback();
    assert(e.timeout_ms==2000 && e.total_energy_>0);
    clock.state.day_of_year=2; clock.state.hour=0; clock.state.minute=0; clock.state.second=1;
    e.timeout();
    assert(e.state==0 && e.pref_.load(&restored) && restored.energy_wh==0 && restored.day_key==2026002);
    e.set_restore(false); auto saves=e.pref_.saves; e.publish_state_and_save(7);
    assert(e.state==7 && e.pref_.saves==saves);
  }
  MeteringDailyEnergy units;
  units.set_restore(false);
  units.publish_state_and_save(1000);
  assert(units.state==1 && units.total_energy_==1000);
  units.set_energy_scale(0.000001f); units.publish_state_and_save(1000000);
  assert(units.state==1 && units.total_energy_==1000000);

  // Small real loads must continue adding energy after a large daily total.
  mock_time::RealTimeClock clock; clock.state.valid=true;
  sensor::Sensor parent;
  MeteringDailyEnergy precise;
  precise.set_time(&clock); precise.set_parent(&parent); precise.set_external_integration(true);
  precise.set_preference_key(102); precise.setup();
  assert(parent.callbacks==0);
  precise.publish_state_and_save(100000.0);
  constexpr double increment=50.0*220.0/3600000.0;
  for(unsigned i=0;i<10000;++i) precise.add_integral_wh(increment);
  assert(std::abs(precise.total_energy_-(100000.0+10000*increment))<1e-7);
  MeteringDailyEnergy::RestoreState saved{};
  assert(precise.pref_.load(&saved) && saved.energy_wh==precise.total_energy_);
  precise.add_integral_wh(NAN); precise.add_integral_wh(INFINITY);
  assert(saved.energy_wh==precise.total_energy_);

  // Stored totals belong to a calendar day, including a year boundary.
  MeteringDailyEnergy same_day;
  same_day.set_time(&clock); same_day.set_parent(&parent); same_day.set_external_integration(true);
  same_day.set_preference_key(102); same_day.setup();
  assert(same_day.total_energy_==saved.energy_wh);
  clock.state.valid=false;
  MeteringDailyEnergy next_day;
  next_day.set_time(&clock); next_day.set_parent(&parent); next_day.set_external_integration(true);
  next_day.set_preference_key(102); next_day.setup(); next_day.add_integral_wh(2.0);
  clock.state.valid=true; clock.state.day_of_year=2; clock.callback();
  assert(next_day.total_energy_==2.0 && next_day.current_day_key_==2026002);
  clock.state.year=2027; clock.state.day_of_year=1; clock.callback();
  assert(next_day.total_energy_==0 && next_day.current_day_key_==2027001);
  next_day.add_integral_wh(-0.25);
  assert(next_day.total_energy_==-0.25);

  // A new device without restored data keeps readings collected before SNTP.
  clock.state.valid=false;
  MeteringDailyEnergy cold;
  cold.set_time(&clock); cold.set_parent(&parent); cold.set_external_integration(true);
  cold.set_preference_key(103); cold.setup(); cold.add_integral_wh(0.75);
  clock.state.valid=true; clock.callback();
  assert(cold.total_energy_==0.75);
  // Only the acquisition segment belonging to today's local day is counted,
  // including a queued interval that ends just before/after midnight.
  simulated_ms=100000;
  clock.state.hour=0; clock.state.minute=0; clock.state.second=0;
  simulated_wall_microseconds=250000; // Today began 250ms ago.
  assert(std::abs(cold.interval_energy_wh(3600,1000,simulated_ms)-0.25)<1e-12);
  assert(std::abs(cold.interval_energy_wh(3600,1000,simulated_ms-100)-0.15)<1e-12);
  assert(cold.interval_energy_wh(3600,1000,simulated_ms-300)==0);
  assert(std::abs(cold.interval_energy_wh(-3600,1000,simulated_ms)+0.25)<1e-12);
  clock.state.second=2; simulated_wall_microseconds=0;
  assert(std::abs(cold.interval_energy_wh(3600,1000,simulated_ms)-1.0)<1e-12);
  clock.state.hour=23; clock.state.minute=59; clock.state.second=59;
  simulated_wall_microseconds=999000;
  assert(std::abs(cold.interval_energy_wh(3600,1000,simulated_ms)-1.0)<1e-12);
  clock.state.hour=0; clock.state.minute=0; clock.state.second=0;
  simulated_ms=100; simulated_wall_microseconds=500000;
  assert(std::abs(cold.interval_energy_wh(3600,1000,UINT32_MAX-99)-0.3)<1e-12);
  // If the wall second rolls over between reads, don't reuse its old fraction.
  simulated_wall_seconds=0; simulated_wall_microseconds=999000;
  assert(cold.interval_energy_wh(3600,1000,simulated_ms)==0);
  clock.state.valid=false;
  assert(std::abs(cold.interval_energy_wh(3600,1000,simulated_ms)-1.0)<1e-12);
  assert(cold.interval_energy_wh(NAN,1000,simulated_ms)==0);
  assert(cold.interval_energy_wh(3600,INFINITY,simulated_ms)==0);
  clock.state.valid=true; simulated_wall_seconds=clock.state.timestamp;
  clock.state.hour=23; clock.state.minute=59; clock.state.second=59;
  uint32_t interval_day=0;
  const double previous_day_delta=cold.interval_energy_wh(3600,1000,simulated_ms,&interval_day);
  assert(interval_day==2027001 && previous_day_delta==1.0);
  clock.state.day_of_year=2; clock.state.hour=0; clock.state.minute=0; clock.state.second=0;
  cold.add_integral_wh(previous_day_delta,interval_day);
  assert(cold.total_energy_==0); // Drain crossed midnight: never put yesterday into today.
  cold.add_integral_wh(0.5,2027002); assert(cold.total_energy_==0.5);
  cold.add_integral_wh(0.25); assert(cold.total_energy_==0.75);
  clock.state.valid=false;
  cold.interval_energy_wh(3600,1000,simulated_ms,&interval_day);
  assert(interval_day==0);
  std::puts("PASS daily energy: double precision, date-aware restore, startup/gaps, signed methods, external integrals, units and millis wrap");
}
"""
    compile_run(PRELUDE + mocks + energy_class + bodies + tests)


def test_demand_persistence_and_intervals():
    methods = ["setup", "loop", "reset_window_", "day_key_", "publish_and_save_maximum_",
               "reset_daily_maximum_", "check_day_", "finish_bucket_", "add_sample", "add_interval_sample"]
    bodies = "\n".join(function(METERING, "MeteringDemandTracker::" + name) for name in methods)
    demand_class = HEADER[HEADER.index("class MeteringDemandTracker {"):HEADER.index("class MeteringPeakTracker {")]
    demand_class = demand_class.replace("protected:", "public:").replace("time::", "mock_time::")
    mocks = r"""
#include <map>
std::map<uint32_t,std::vector<uint8_t>> preference_data;
struct ESPPreferenceObject {
  uint32_t key{0};
  template<typename T> bool load(T *out) {
    auto it=preference_data.find(key);
    if(it==preference_data.end() || it->second.size()!=sizeof(T)) return false;
    std::memcpy(out,it->second.data(),sizeof(T)); return true;
  }
  template<typename T> bool save(const T *in) {
    auto &bytes=preference_data[key]; bytes.resize(sizeof(T));
    std::memcpy(bytes.data(),in,sizeof(T)); return true;
  }
};
struct Preferences {
  template<typename T> ESPPreferenceObject make_preference(uint32_t key) {return {key};}
} preferences;
Preferences *global_preferences=&preferences;
namespace sensor {struct Sensor {
  float state{NAN}; unsigned publishes{0};
  void publish_state(float value) {state=value; ++publishes;}
  uint32_t get_object_id_hash() const {return 77;} // Identical names in different subdevices.
};}
struct ESPTime {
  bool valid{true}; unsigned year{2026}, day_of_year{5};
  bool is_valid() const {return valid;}
};
namespace mock_time {struct RealTimeClock {ESPTime state; ESPTime now() const {return state;}};}
"""
    tests = r"""
int main() {
  mock_time::RealTimeClock clock; sensor::Sensor sensor_a,sensor_b;
  MeteringDemandTracker a,b;
  a.set_maximum_sensor(&sensor_a); b.set_maximum_sensor(&sensor_b);
  a.set_time(&clock); b.set_time(&clock);
  a.set_preference_key(201); b.set_preference_key(202);
  a.setup(); b.setup(); a.loop(); b.loop();
  a.publish_and_save_maximum_(100); b.publish_and_save_maximum_(200);
  MeteringDemandTracker restored_a,restored_b;
  restored_a.set_maximum_sensor(&sensor_a); restored_b.set_maximum_sensor(&sensor_b);
  restored_a.set_time(&clock); restored_b.set_time(&clock);
  restored_a.set_preference_key(201); restored_b.set_preference_key(202);
  restored_a.setup(); restored_b.setup(); restored_a.loop(); restored_b.loop();
  assert(sensor_a.state==100 && sensor_b.state==200);
  clock.state.day_of_year=6; restored_a.loop(); restored_b.loop();
  assert(std::isnan(sensor_a.state) && std::isnan(sensor_b.state));

  sensor::Sensor demand;
  MeteringDemandTracker tracker;
  tracker.set_interval(10000); tracker.set_demand_sensor(&demand); tracker.setup();
  // All queued frames may be consumed in the same mainloop tick. Their actual
  // fractional acquisition duration, not that tick, defines the mean.
  for(unsigned i=0;i<40;++i) tracker.add_interval_sample(100,222.5,9000);
  assert(std::isnan(demand.state));
  tracker.add_interval_sample(100,1100,10100);
  assert(std::abs(demand.state-100)<1e-6 && tracker.bucket_count_==2);
  tracker.add_interval_sample(300,5000,15100);
  assert(std::abs(demand.state-200)<1e-6);
  tracker.add_interval_sample(NAN,220,15320);
  assert(std::isnan(demand.state) && tracker.bucket_count_==0);
  tracker.add_interval_sample(100,10000,25320);
  assert(demand.state==100);
  tracker.add_interval_sample(INFINITY,220,25540);
  assert(std::isnan(demand.state));
  tracker.add_interval_sample(100,30001,55541);
  assert(tracker.bucket_count_==0);

  // I2C retains left-sample integration and its startup/gap baseline.
  MeteringDemandTracker legacy;
  legacy.set_interval(5000); legacy.set_demand_sensor(&demand); legacy.setup();
  legacy.add_sample(100,1000); legacy.add_sample(200,2000); legacy.add_sample(200,6000);
  assert(std::abs(demand.state-180)<1e-6);
  legacy.add_sample(200,60000);
  assert(std::isnan(demand.state));

  // The local date can advance while queued acquisition endpoints still refer
  // to yesterday. Start today's maximum guard at actual observation, never at
  // that old endpoint, and do not let unsigned subtraction bypass the guard.
  sensor::Sensor midnight_max;
  MeteringDemandTracker midnight;
  midnight.set_interval(60000); midnight.set_maximum_sensor(&midnight_max);
  midnight.set_time(&clock); midnight.set_restore(false); midnight.setup();
  simulated_ms=100000; midnight.loop();
  for(unsigned i=1;i<=12;++i) {
    simulated_ms=100000+i*5000; midnight.add_interval_sample(10,5000,simulated_ms);
  }
  assert(midnight_max.state==10);
  ++clock.state.day_of_year; simulated_ms=162000;
  midnight.add_interval_sample(1000,5000,160000); // 2-second main-loop backlog.
  assert(std::isnan(midnight_max.state) && midnight.daily_window_start_ms_==162000);
  for(unsigned i=1;i<=12;++i) {
    simulated_ms=160000+i*5000; midnight.add_interval_sample(20,5000,simulated_ms);
  }
  assert(std::isnan(midnight_max.state)); // The old anchor would permit this maximum 2s early.
  simulated_ms=225000; midnight.add_interval_sample(20,5000,simulated_ms);
  assert(midnight_max.state==20);

  // A restored empty maximum gets the same guard; a valid same-day maximum
  // remains immediately restorable, including near millis() rollover.
  midnight.publish_and_save_maximum_(NAN);
  MeteringDemandTracker empty_restore;
  empty_restore.set_interval(60000); empty_restore.set_maximum_sensor(&midnight_max);
  empty_restore.set_time(&clock); empty_restore.setup(); empty_restore.restored_state_valid_=true;
  empty_restore.restored_state_={midnight.current_day_key_,NAN};
  simulated_ms=UINT32_MAX-1000; empty_restore.check_day_(simulated_ms-1000);
  assert(empty_restore.daily_window_start_ms_==simulated_ms && std::isnan(midnight_max.state));
  empty_restore.add_interval_sample(30,5000,simulated_ms-500);
  assert(std::isnan(midnight_max.state));
  for(unsigned i=1;i<=12;++i) {
    simulated_ms=uint32_t(UINT32_MAX-1000)+i*5000;
    empty_restore.add_interval_sample(30,5000,simulated_ms);
  }
  assert(midnight_max.state==30);
  MeteringDemandTracker valid_restore;
  valid_restore.set_interval(60000); valid_restore.set_maximum_sensor(&midnight_max);
  valid_restore.set_time(&clock); valid_restore.setup(); valid_restore.restored_state_valid_=true;
  valid_restore.restored_state_={midnight.current_day_key_,75};
  valid_restore.check_day_(simulated_ms-1000);
  assert(midnight_max.state==75 && valid_restore.daily_maximum_valid_);
  assert(uint32_t(simulated_ms-valid_restore.daily_window_start_ms_)==60000);
  std::puts("PASS demand: independent restore, midnight/backlog guards, fractional intervals, millis wrap, gaps and I2C integration");
}
"""
    compile_run(PRELUDE + mocks + demand_class + bodies + tests)


def test_energy_filters():
    spec = importlib.util.spec_from_file_location("ev_test", ROOT / "components/emporiavue/__init__.py")
    component = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(component)
    cases = [
        ({}, 0.001, 0),
        ({"filters": [{"throttle": "5s"}]}, 0.001, 0),
        ({"filters": [{"multiply": 0.001}, {"throttle": "5s"}]}, 0.001, 0),
        ({"filters": [{"throttle": "5s"}, {"multiply": 0.001}]}, 0.001, 0),
        ({"filters": [{"multiply": 1.1}]}, 0.0011, 1),
        ({"unit_of_measurement": "Wh"}, 1.0, 0),
        ({"unit_of_measurement": "MWh"}, 0.000001, 0),
    ]
    # Reproduce the original local-filter override of a global .001 conversion.
    parent = component._apply_filter_default_to_sensor(
        {"energy": {"filters": [{"throttle": "5s"}]}}, "energy",
        {"energy": [{"multiply": 0.001}]}, "test",
    )
    cases.append((parent["energy"], 0.001, 0))
    for index, (config, expected, count) in enumerate(cases):
        validated = component._validate_energy_sensor({"name": f"Energy {index}", **config})
        filters = validated["filters"]
        multipliers = [f["multiply"] for f in filters if "multiply" in f]
        result = component.ENERGY_UNIT_SCALES[validated["unit_of_measurement"]]
        for multiplier in multipliers:
            result *= multiplier
        assert len(multipliers) == count and abs(result - expected) < 1e-12
    print("PASS energy units: bare, local/global throttle, legacy conversion, Wh/kWh/MWh and calibration")

    # Storage is tied to the logical measurement path, not a display name or owner.
    paths = [
        "circuits.cir1.energy.both", "circuits.cir2.energy.both",
        "circuits.cir1.energy.positive", "circuits.cir1.energy.negative",
        "circuits.cir1.maximum_power_demand", "circuits.cir2.maximum_power_demand",
        "circuits.cir1.maximum_current_demand", "mains.line_1.energy.both", "groups.grid.energy.both",
    ]
    keys = [component._metering_preference_key(path) for path in paths]
    assert len(keys) == len(set(keys)) and all(keys)
    for path, key in zip(paths, keys):
        assert component._metering_preference_key(path) == key
    print("PASS stable metering persistence keys: circuits, mains, groups and energy directions")


def test_metering_timeout():
    methods = ["submit_metering_frame_", "check_metering_timeout_", "invalidate_metering_",
               "apply_power_direction_", "publish_power_outputs_"]
    bodies = [function(METERING, "EmporiaVueComponent::" + name) for name in methods]
    declarations = [re.search(
        r"^  (?:static )?[\w:<>]+\s+" + re.escape(name) + r"\([^;]*\)(?: const)?;", HEADER, re.M
    ).group().strip() for name in methods]
    # Every measurement sensor touched by the real invalidation path gets a
    # separate mock. Counters verify that only transient analysis is reset.
    getters = sorted(set(re.findall(r"->(get_\w+_sensor)\(\)", bodies[2])))
    getters.remove("get_line_detection_sensor")
    getter_methods = "\n".join(f"sensor::Sensor *{name}() {{return &sensors[{index}];}}" for index, name in enumerate(getters))
    power_class = HEADER[HEADER.index("class MeteringPowerOutput {"):HEADER.index("class MeteringDemandTracker")]
    peak_class = HEADER[HEADER.index("class MeteringPeakTracker {"):HEADER.index("class EmporiaVueComponent")]
    peak_methods = "\n".join(function(METERING, "MeteringPeakTracker::" + name) for name in
                             ["finish_window_", "loop", "invalidate_window", "add_sample"])
    mocks = r"""
namespace sensor {struct Sensor {
  float state{1}; unsigned count{0};
  void publish_state(float value) {state=value; ++count;}
};}
struct Text {std::string state; void publish_state(const char *value) {state=value;}};
struct Detection {unsigned resets{0}; void reset_all() {++resets;}};
struct MeteringDailyEnergy {
  void add_integral_wh(double,uint32_t=0) {}
  double interval_energy_wh(float power,double duration,uint32_t,uint32_t *day=nullptr) const {
    if(day!=nullptr) *day=0; return power*duration/3600000.0;
  }
};
"""
    node = r"""
struct Node {
  sensor::Sensor sensors[32], raw, visible;
  std::vector<MeteringPowerOutput> outputs{{0,&raw,&visible}};
  Text text;
  Detection detection, assignment;
  struct Analysis {unsigned resets{0}; void reset() {++resets;}} analysis;
  Analysis& get_analysis_tracker() {return analysis;}
  void clear_pending_analysis() {}
  float energy{123}, maximum{456};
  int saved_line{2};
  unsigned power_gaps{0}, current_gaps{0}, peak_resets{0};
  const std::vector<MeteringPowerOutput>& get_power_outputs() {return outputs;}
  Text* get_line_detection_sensor() {return &text;}
  Detection& get_line_detection_state() {return detection;}
  Detection& get_auto_line_detection_state() {return assignment;}
  void add_power_demand_sample(float value, uint32_t) {assert(std::isnan(value)); ++power_gaps;}
  void add_current_demand_sample(float value, uint32_t) {assert(std::isnan(value)); ++current_gaps;}
  void invalidate_peak(uint32_t) {++peak_resets;}
""" + getter_methods + "\n};\n"
    component = r"""
struct MeteringFrame {
  bool valid{true}; uint32_t timestamp_ms{0}, sequence{0}, acquisition_epoch{0};
  MeteringTransport transport{MeteringTransport::SPI}; uint8_t quality_flags{0};
};
class EmporiaVueComponent {public:
  uint32_t metering_timeout_ms_{2000}, last_metering_frame_ms_{0}, last_unavailable_publish_ms_{0};
  bool metering_data_stale_{true}, last_metering_sequence_valid_{false};
  uint32_t last_metering_sequence_{0}, i2c_missing_readings_window_{0};
  uint32_t last_metering_acquisition_epoch_{0};
  MeteringTransport last_metering_transport_{MeteringTransport::UNKNOWN};
  std::vector<Node*> metering_phases_, metering_virtual_lines_, metering_ct_clamps_, metering_groups_;
  unsigned published{0};
  void publish_metering_frame_(const MeteringFrame&,bool) {++published;}
""" + "\n".join(declarations) + "\n};\n"
    tests = r"""
int main() {
  for (auto transport : {MeteringTransport::SPI,MeteringTransport::I2C}) {
    EmporiaVueComponent c; Node ct, group, phase, virtual_line;
    c.metering_ct_clamps_={&ct}; c.metering_groups_={&group};
    c.metering_phases_={&phase}; c.metering_virtual_lines_={&virtual_line};
    MeteringFrame frame; frame.transport=transport;
    simulated_ms=1000; c.check_metering_timeout_(simulated_ms);
    assert(ct.raw.count==0); // Not started yet.
    frame.timestamp_ms=simulated_ms; frame.sequence=1; c.submit_metering_frame_(frame,true);
    simulated_ms=2000; c.check_metering_timeout_(simulated_ms); assert(ct.raw.count==0);
    simulated_ms=3001; c.check_metering_timeout_(simulated_ms);
    assert(std::isnan(ct.raw.state) && std::isnan(group.raw.state));
    assert(ct.power_gaps==1 && ct.current_gaps==1 && group.power_gaps==1);
    assert(ct.detection.resets==1 && ct.assignment.resets==1 && ct.text.state=="unavailable");
    assert(ct.energy==123 && ct.maximum==456 && ct.saved_line==2);
    const auto count=ct.raw.count;
    simulated_ms=3500; c.check_metering_timeout_(simulated_ms); assert(ct.raw.count==count);
    simulated_ms=4001; c.check_metering_timeout_(simulated_ms); assert(ct.raw.count==count+1);
    assert(ct.power_gaps==1 && ct.detection.resets==1); // No repeated analysis resets.
    c.submit_metering_frame_(frame,true); assert(c.published==1); // Old queued frame rejected.
    frame.timestamp_ms=simulated_ms; frame.sequence=transport==MeteringTransport::SPI ? 2 : 4;
    c.submit_metering_frame_(frame,true);
    assert(c.published==2 && !c.metering_data_stale_);
    assert(c.i2c_missing_readings_window_==(transport==MeteringTransport::I2C ? 2U : 0U));
    simulated_ms=8000; frame.timestamp_ms=simulated_ms; ++frame.sequence;
    c.submit_metering_frame_(frame,true); // Main loop stalled: reset even without a timeout call.
    assert(ct.power_gaps==2 && c.published==3);
    frame.valid=false; c.submit_metering_frame_(frame,true); assert(c.published==3);
    frame.valid=true; simulated_ms=UINT32_MAX-1000; frame.timestamp_ms=simulated_ms;
    ++frame.sequence; c.submit_metering_frame_(frame,true);
    auto resets=ct.power_gaps;
    simulated_ms+=1500; c.check_metering_timeout_(simulated_ms); assert(ct.power_gaps==resets);
    frame.timestamp_ms=simulated_ms; ++frame.sequence;
    c.submit_metering_frame_(frame,true); assert(ct.power_gaps==resets);
    if(transport==MeteringTransport::SPI) {
      ++frame.acquisition_epoch; ++frame.sequence;
      c.submit_metering_frame_(frame,false);
      assert(ct.power_gaps==resets+1); // New stream must not bridge accumulators.
      frame.sequence+=2;
      c.submit_metering_frame_(frame,false);
      assert(ct.power_gaps==resets+2); // Explicit completed-window loss is a gap too.
    }
  }
  MeteringPeakTracker peak; sensor::Sensor current, crest;
  peak.set_current_peak_sensor(&current); peak.set_current_crest_factor_sensor(&crest);
  peak.add_sample(10,20,0); peak.invalidate_window(2000); peak.loop(5000);
  assert(std::isnan(current.state) && std::isnan(crest.state));
  peak.add_sample(1,2,6000); peak.loop(11000);
  assert(current.state==1 && crest.state==2); // Old peak must not survive the gap.
  std::puts("PASS I2C/SPI freshness: stale queue, stalled loop, retries, saved state, peaks and millis wrap");
}
"""
    compile_run(PRELUDE + mocks + power_class + peak_class + node + component + "\n".join(bodies) + peak_methods + tests)


if __name__ == "__main__":
    test_spi_windows()
    test_spi_error_classification()
    test_spi_status_logging()
    test_current_peak_preservation()
    test_fundamental_analysis_math()
    test_energy_gaps()
    test_demand_persistence_and_intervals()
    test_energy_filters()
    test_metering_timeout()
