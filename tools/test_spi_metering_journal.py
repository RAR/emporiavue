#!/usr/bin/env python3
"""Host regression for the production main-thread SPI measurement journal.

Only hardware, ESPHome I/O, and the already separately tested raw-to-physical
conversion are mocked. The production FIFO drain, continuity, publication,
directional energy, group cache, demand, peak and analysis paths are compiled.
"""

import re

from test_esphome_metering import HEADER, METERING, SPI, PRELUDE, compile_run, function


def declaration(name):
    match = re.search(r"^  (?:static )?[\w:<>]+\s+" + re.escape(name) +
                      r"\([^;]*\)(?: const)?;", HEADER, re.M)
    assert match, name
    return match.group().strip()


def test_journal():
    names = ["publish_metering_frame_", "submit_metering_frame_", "invalidate_metering_",
             "apply_power_direction_", "publish_power_outputs_", "calculate_group_power_",
             "prepare_ct_power_analysis_", "publish_queued_spi_metering_"]
    bodies = [function(SPI if name == "publish_queued_spi_metering_" else METERING,
                       "EmporiaVueComponent::" + name) for name in names]
    structs = HEADER[HEADER.index("  struct MeteringPhase {"):HEADER.index("  struct SpiRawScan {")]
    classes = (
        HEADER[HEADER.index("class MeteringPowerFilters {"):HEADER.index("class EmporiaVueComponent :")]
        + HEADER[HEADER.index("class MeteringPhaseConfig {"):HEADER.index("class MeteringCalibrationNumber :")]
        + HEADER[HEADER.index("class MeteringLineDetectionState {"):HEADER.index("class EmporiaVueBackupFirmwareButton :")]
    ).replace("protected:", "public:")
    trackers = "\n".join(function(METERING, owner + "::" + name) for owner, methods in (
        ("MeteringDemandTracker", ["setup", "loop", "reset_window_", "day_key_",
                                   "publish_and_save_maximum_", "reset_daily_maximum_", "check_day_",
                                   "finish_bucket_", "add_sample", "add_interval_sample"]),
        ("MeteringPeakTracker", ["finish_window_", "loop", "invalidate_window", "add_sample"]),
        ("MeteringAnalysisTracker", ["add_sample"]),
    ) for name in methods)
    mocks = r"""
#include <deque>
#define USE_ESP32
namespace journal_test {
namespace sensor { struct Sensor {
  float state{NAN}; std::vector<float> published;
  std::function<void(float)> callback;
  void publish_state(float value) {
    state=value; published.push_back(value); if(callback) callback(value);
  }
}; }
namespace text_sensor { struct TextSensor {
  std::string state; void publish_state(const char *value) {state=value;}
}; }
struct ESPTime {unsigned year{2026},day_of_year{284}; bool is_valid() const {return true;}};
namespace time {struct RealTimeClock {ESPTime now() const {return {};}};}
struct ESPPreferenceObject {
  template<class T> bool load(T*) {return false;}
  template<class T> bool save(const T*) {return true;}
};
struct Preferences {
  template<class T> ESPPreferenceObject make_preference(uint32_t) {return {};}
} preferences;
auto global_preferences=&preferences;
class MeteringCalibrationNumber;
class MeteringCurrentGainNumber;
class MeteringCurrentPhaseNumber;
class MeteringLineSelect;
// Midnight clipping and date-tag persistence have their own production tests.
// Keep the exact public API here so output batching is still exercised.
struct MeteringDailyEnergy {
  double total{0}; unsigned publications{0};
  double interval_energy_wh(float power,double duration,uint32_t,uint32_t *day=nullptr) const {
    if(day) *day=2026284; return double(power)*duration/3600000.0;
  }
  void add_integral_wh(double value,uint32_t day=0) {
    assert(day==0 || day==2026284); total+=value; ++publications;
  }
};
using UBaseType_t=unsigned;
static constexpr int pdTRUE=1,pdFALSE=0;
struct HostQueue {
  size_t capacity,element_size; std::deque<std::vector<uint8_t>> records;
};
using QueueHandle_t=HostQueue*;
UBaseType_t uxQueueMessagesWaiting(QueueHandle_t q) {return q->records.size();}
int xQueueSend(QueueHandle_t q,const void *record,unsigned) {
  if(q->records.size()==q->capacity) return pdFALSE;
  const auto *bytes=static_cast<const uint8_t*>(record);
  q->records.emplace_back(bytes,bytes+q->element_size); return pdTRUE;
}
int xQueueReceive(QueueHandle_t q,void *record,unsigned) {
  if(q->records.empty()) return pdFALSE;
  std::memcpy(record,q->records.front().data(),q->element_size);
  q->records.pop_front(); return pdTRUE;
}
"""
    component = r"""
class EmporiaVueComponent { public:
""" + structs + "\n" + "\n".join(declaration(name) for name in names) + r"""
  uint32_t metering_timeout_ms_{2000},last_metering_frame_ms_{0},last_unavailable_publish_ms_{0};
  bool metering_data_stale_{true},last_metering_sequence_valid_{false};
  uint32_t last_metering_sequence_{0},last_metering_acquisition_epoch_{0},i2c_missing_readings_window_{0};
  uint32_t metering_calculation_generation_{0},spi_metering_stale_windows_{0};
  MeteringTransport last_metering_transport_{MeteringTransport::UNKNOWN};
  float minimum_apparent_power_{5},minimum_fundamental_current_{0.02f};
  std::vector<MeteringPhaseConfig*> metering_phases_;
  std::vector<MeteringVirtualLineConfig*> metering_virtual_lines_;
  std::vector<MeteringCTClampConfig*> metering_ct_clamps_;
  std::vector<MeteringGroupConfig*> metering_groups_;
  QueueHandle_t spi_metering_queue_{nullptr};
  mutable unsigned physical_calculations{0},fundamental_calculations{0};
  unsigned detection_updates{0};
  void update_line_detection_(const MeteringFrame&,MeteringCTClampConfig*) {++detection_updates;}
  bool calculate_ct_power_(const MeteringFrame &frame,const MeteringCTClampConfig *ct,float *power) const {
    ++physical_calculations;
    *power=ct->apply_power_filters(frame.clamps[ct->get_input_port()].power_raw_by_phase[0]);
    return std::isfinite(*power);
  }
  bool calculate_ct_measurement_(const MeteringFrame &frame,const MeteringCTClampConfig *ct,
                                  MeteringCTMeasurement *value) const {
    value->has_power=calculate_ct_power_(frame,ct,&value->power);
    value->has_current=true; value->current=frame.clamps[ct->get_input_port()].current_raw;
    value->has_voltage=true; value->voltage=230;
    value->has_apparent_power=true; value->apparent_power=value->current*230;
    value->has_power_factor=true; value->power_factor=value->power/value->apparent_power;
    return true;
  }
  bool calculate_ct_fundamental_analysis_(const MeteringFrame &frame,const MeteringCTClampConfig *ct,
                                          MeteringCTMeasurement *value) const {
    ++fundamental_calculations;
    const auto &raw=frame.clamps[ct->get_input_port()];
    value->has_fundamental_analysis=raw.current_fundamental_valid;
    value->fundamental_active_power=raw.current_fundamental_i_raw;
    value->fundamental_reactive_power=raw.current_fundamental_q_raw;
    value->fundamental_voltage=230;
    value->fundamental_current=std::hypot(value->fundamental_active_power,value->fundamental_reactive_power)/230;
    value->fundamental_power_factor=std::fabs(value->fundamental_active_power)/
      std::hypot(value->fundamental_active_power,value->fundamental_reactive_power);
    value->displacement_angle=std::atan2(value->fundamental_reactive_power,value->fundamental_active_power)*180/M_PI;
    return value->has_fundamental_analysis;
  }
  bool calculate_line_to_line_voltage_(const MeteringFrame&,const MeteringPhaseConfig*,
                                        const MeteringPhaseConfig*,float *value) const {*value=400;return true;}
};
"""
    tests = r"""
using Frame=EmporiaVueComponent::MeteringFrame;
void near(double actual,double expected,double tolerance=1e-6) {assert(std::abs(actual-expected)<tolerance);}
struct Fixture {
  EmporiaVueComponent c;
  HostQueue queue{16,sizeof(Frame),{}};
  MeteringPhaseConfig phase;
  MeteringCTClampConfig a,b;
  MeteringGroupConfig group,nested;
  sensor::Sensor power,raw,current,voltage,reactive,pf,angle,peak,crest,demand,current_demand;
  sensor::Sensor group_signed,group_import,group_export,group_demand,nested_power;
  MeteringDailyEnergy energy,net_energy,import_energy,export_energy;
  unsigned a_filter_calls{0},group_filter_calls{0},nested_filter_calls{0};
  Fixture() {
    c.spi_metering_queue_=&queue; c.metering_phases_={&phase};
    phase.set_calibration(1); phase.set_voltage_sensor(&voltage);
    a.set_input_port(3); a.set_phase(&phase); b.set_input_port(4); b.set_phase(&phase);
    a.add_power_lambda_filter([this](float value){++a_filter_calls;return value*2;});
    a.add_power_output(0,&raw,&power,&energy); a.set_current_sensor(&current);
    a.set_fundamental_reactive_power_sensor(&reactive); a.set_fundamental_power_factor_sensor(&pf);
    a.set_displacement_angle_sensor(&angle); a.set_analysis_interval(600);
    a.set_current_peak_sensor(&peak); a.set_current_crest_factor_sensor(&crest); a.set_peak_interval(1000);
    a.set_power_demand_sensor(&demand); a.set_current_demand_sensor(&current_demand); a.setup_demand();
    group.add_ct_clamp_term(&a,1); group.add_ct_clamp_term(&b,-1);
    group.add_power_lambda_filter([this](float value){++group_filter_calls;return value*1.5f;});
    group.add_power_output(0,nullptr,&group_signed,&net_energy);
    group.add_power_output(1,nullptr,&group_import,&import_energy);
    group.add_power_output(2,nullptr,&group_export,&export_energy);
    group.set_power_demand_sensor(&group_demand); group.setup_demand();
    nested.add_group_term(&group,1); nested.add_ct_clamp_term(&a,1);
    nested.add_power_lambda_filter([this](float value){++nested_filter_calls;return value;});
    nested.add_power_output(0,nullptr,&nested_power);
    c.metering_ct_clamps_={&a,&b};
    // Resolve a nested group first; the later top-level group must reuse cache.
    c.metering_groups_={&nested,&group};
  }
  Frame make(uint32_t sequence,int watts=100,float q=30,float p=10,float amps_peak=10) {
    Frame frame; frame.valid=true; frame.transport=MeteringTransport::SPI;
    frame.sequence=sequence; frame.acquisition_epoch=1; frame.timestamp_ms=800+sequence*200;
    frame.duration_ms=200.5; frame.phases[0].voltage_raw=230+sequence;
    frame.clamps[3].power_raw_by_phase[0]=watts; frame.clamps[4].power_raw_by_phase[0]=20;
    frame.clamps[3].current_raw=frame.clamps[4].current_raw=1;
    frame.clamps[3].current_fundamental_valid=true;
    frame.clamps[3].current_fundamental_i_raw=p; frame.clamps[3].current_fundamental_q_raw=q;
    frame.clamps[3].current_peak_valid=true;
    frame.clamps[3].current_peak_raw=std::lround(amps_peak*170496/775);
    return frame;
  }
  bool enqueue(const Frame &frame) {return xQueueSend(&queue,&frame,0)==pdTRUE;}
};
void run_tests() {
  {
    Fixture f;
    const int powers[]{100,0,-100,0,25};
    const float qs[]{30,20,10,200,300};
    for(unsigned i=0;i<5;++i) assert(f.enqueue(f.make(i+1,powers[i],qs[i],10*(i+1),i==0?10:2)));
    simulated_ms=1900; // Five acquisition windows, drained in one main-loop tick.
    f.c.publish_queued_spi_metering_(); assert(f.queue.records.empty());
    near(f.energy.total,50*200.5/3600000.0);
    near(f.net_energy.total,-75*200.5/3600000.0);
    near(f.import_energy.total,315*200.5/3600000.0);
    near(f.export_energy.total,390*200.5/3600000.0);
    assert(f.energy.publications==1 && f.net_energy.publications==1);
    assert(f.power.published.size()==1 && f.raw.published.size()==1 && f.voltage.published.size()==1);
    near(f.power.state,50); near(f.group_signed.state,45); near(f.nested_power.state,95);
    near(f.group_import.state,45); near(f.group_export.state,0); near(f.voltage.state,235);
    assert(f.c.physical_calculations==10 && f.c.detection_updates==10);
    assert(f.a_filter_calls==5 && f.group_filter_calls==5 && f.nested_filter_calls==5);
    // A complete analysis window occurs in the third queued frame, not the last.
    assert(f.angle.published.size()==1 && f.reactive.published.size()==1);
    near(f.angle.state,45); near(f.reactive.state,20); near(f.pf.state,std::sqrt(0.5));
    near(f.a.analysis_tracker_.duration_ms_,401);
    near(f.a.power_demand_.current_bucket_elapsed_ms_,1002.5);
    near(f.a.power_demand_.current_bucket_integral_,50*200.5);
    near(f.a.current_demand_.current_bucket_integral_,1002.5);
    near(f.group.power_demand_.current_bucket_integral_,-75*200.5);
    f.a.loop_peak(2000); assert(f.peak.published.size()==1);
    near(f.peak.state,10,0.003); near(f.crest.state,10,0.003);
    std::puts("PASS SPI journal: all acquisition windows feed energy/demand/peak/analysis, latest display only");
  }
  {
    Fixture f; f.queue.capacity=2;
    assert(f.enqueue(f.make(1))); assert(f.enqueue(f.make(2)));
    assert(!f.enqueue(f.make(3))); // Bounded typed FIFO must not overwrite an older window.
    simulated_ms=1400; f.c.publish_queued_spi_metering_();
    assert(f.c.last_metering_sequence_==2); near(f.energy.total,400*200.5/3600000.0);
    near(f.a.analysis_tracker_.duration_ms_,401);
    assert(f.enqueue(f.make(4,50,1,20,2))); simulated_ms=1700;
    f.c.publish_queued_spi_metering_();
    // Completed energy remains, unfinished accumulators cannot span the drop.
    near(f.energy.total,500*200.5/3600000.0);
    near(f.a.analysis_tracker_.duration_ms_,200.5);
    near(f.a.power_demand_.current_bucket_integral_,100*200.5);
    near(f.a.peak_tracker_.maximum_current_peak_,2,0.003);
    auto restarted=f.make(5,25,2,30,3); ++restarted.acquisition_epoch;
    assert(f.enqueue(restarted)); simulated_ms=1900; f.c.publish_queued_spi_metering_();
    near(f.a.analysis_tracker_.duration_ms_,200.5);
    near(f.a.power_demand_.current_bucket_integral_,50*200.5);
    near(f.energy.total,550*200.5/3600000.0);
    std::puts("PASS SPI journal: FIFO overflow and acquisition epoch reset unfinished state without losing completed energy");
  }
  {
    Fixture f;
    assert(f.enqueue(f.make(1))); assert(f.enqueue(f.make(2)));
    // A producer publishes while the last snapshot entry is displayed.
    bool appended=false;
    f.power.callback=[&](float){if(!appended){appended=true;assert(f.enqueue(f.make(3)));}};
    simulated_ms=1500; f.c.publish_queued_spi_metering_();
    assert(f.queue.records.size()==1 && f.c.last_metering_sequence_==2);
    near(f.energy.total,400*200.5/3600000.0);
    f.c.publish_queued_spi_metering_(); assert(f.queue.records.empty());
    near(f.energy.total,600*200.5/3600000.0);
    assert(f.power.published.size()==2 && f.a_filter_calls==3);
    std::puts("PASS SPI journal: drain is bounded to its entry snapshot even when producer continues");
  }
  {
    Fixture f; assert(f.enqueue(f.make(1))); assert(f.enqueue(f.make(2)));
    simulated_ms=3201; // Both are stale; neither energy nor filters may consume them.
    f.c.publish_queued_spi_metering_(); assert(f.c.spi_metering_stale_windows_==2);
    assert(f.energy.total==0 && f.a_filter_calls==0 && f.power.published.empty());
    auto frame=f.make(3); frame.timestamp_ms=simulated_ms; assert(f.enqueue(frame));
    f.c.publish_queued_spi_metering_(); near(f.energy.total,200*200.5/3600000.0);
    std::puts("PASS SPI journal: stale records are diagnosed and excluded from integration");
  }
}
"""
    compile_run(PRELUDE + mocks + classes + component + trackers + "\n".join(bodies) + tests +
                "\n} // namespace journal_test\nint main() {journal_test::run_tests();}\n")


if __name__ == "__main__":
    test_journal()
