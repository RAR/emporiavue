#!/usr/bin/env python3
"""Exercise the production duration-weighted fundamental P/Q analysis window."""
import importlib.util
from test_esphome_metering import ROOT, HEADER, METERING, PRELUDE, compile_run, function


def test_analysis_interval():
    tracker = HEADER[HEADER.index("class MeteringAnalysisTracker {"):HEADER.index("class MeteringCTClampConfig {")]
    measurement = HEADER[HEADER.index("  struct MeteringCTMeasurement {"):HEADER.index("  struct SpiRawScan {")]
    methods = [function(METERING, "EmporiaVueComponent::" + name) for name in
               ["calculate_ct_fundamental_analysis_", "prepare_ct_power_analysis_"]]
    declarations = [body[:body.index("{")].replace("EmporiaVueComponent::", "").rstrip() + ";" for body in methods]
    # Exercise the actual runtime-control setters, not copies of their reset logic.
    controls = HEADER[HEADER.index("class MeteringCTClampConfig {"):HEADER.index("class MeteringGroupConfig {")]
    controls = "\n".join(line[2:] if line.startswith("  ") else line for line in controls.splitlines())
    control_methods = "\n".join(function(controls, name) for name in
                                ["set_phase", "set_line_pair", "set_current_gain", "set_current_phase_correction",
                                 "clear_pending_analysis"])
    mocks = r"""
namespace sensor {struct Sensor {};}
struct MeteringFrame {
  MeteringTransport transport{MeteringTransport::SPI}; float duration_ms{200};
};
struct MeteringPhaseConfig {float calibration{0.022f}; float get_calibration() const {return calibration;}};
struct RuntimeControls {
  MeteringPhaseConfig *phase_{nullptr}, *line_pair_phase_b_{nullptr}; bool line_pair_{false};
  MeteringAnalysisTracker analysis_tracker_;
  bool pending_analysis_result_valid_{false};
  float current_gain_{1}, current_phase_correction_degrees_{0};
  struct Detection {void reset_all() {}} line_detection_state_, auto_line_detection_state_;
""" + control_methods + r"""
};
struct MeteringCTClampConfig {
  MeteringAnalysisTracker tracker;
  MeteringPhaseConfig a, b; bool pair{false};
  sensor::Sensor reactive, factor, angle, thd;
  bool want_reactive{true}, want_factor{true}, want_angle{true}, want_thd{true};
  uint32_t get_analysis_interval() const {return tracker.get_interval();}
  MeteringAnalysisTracker &get_analysis_tracker() {return tracker;}
  bool has_fundamental_power_analysis() const {return want_reactive || want_factor || want_angle;}
  const MeteringPhaseConfig *get_phase() const {return &a;}
  const MeteringPhaseConfig *get_line_pair_phase_b() const {return pair ? &b : nullptr;}
  sensor::Sensor *get_fundamental_reactive_power_sensor() const {return want_reactive ? const_cast<sensor::Sensor*>(&reactive) : nullptr;}
  sensor::Sensor *get_fundamental_power_factor_sensor() const {return want_factor ? const_cast<sensor::Sensor*>(&factor) : nullptr;}
  sensor::Sensor *get_displacement_angle_sensor() const {return want_angle ? const_cast<sensor::Sensor*>(&angle) : nullptr;}
  sensor::Sensor *get_current_thd_sensor() const {return want_thd ? const_cast<sensor::Sensor*>(&thd) : nullptr;}
};
class EmporiaVueComponent {public:
  float minimum_fundamental_current_{0.02f}, vi{230}, vq{0}, ci{1}, cq{0}; bool valid{true};
  bool calculate_ct_fundamental_phasors_(const MeteringFrame&,const MeteringCTClampConfig*,float *a,
                                         float *b,float *c,float *d,bool) const {
    if (!valid) return false;
    *a=vi; *b=vq; *c=ci; *d=cq; return true;
  }
""" + "\n".join(declarations) + r"""
};
struct Fixture {
  EmporiaVueComponent component; MeteringCTClampConfig ct; MeteringFrame frame; MeteringCTMeasurement m;
  Fixture() {ct.tracker.set_interval(1000);}
  bool sample(float p, float q, float duration=200) {
    component.ci=p/component.vi; component.cq=q/component.vi;
    frame.duration_ms=duration;
    m=MeteringCTMeasurement{}; m.has_current=true; m.current=std::hypot(component.ci,component.cq)*1.1f;
    component.calculate_ct_fundamental_analysis_(frame,&ct,&m);
    return component.prepare_ct_power_analysis_(frame,&ct,&m);
  }
};
void near(float a,float b,float tolerance=1e-4f) {assert(std::fabs(a-b)<tolerance);}
"""
    tests = r"""
int main() {
  {
    Fixture f;
    for (int i=0;i<4;i++) assert(!f.sample(230,230));
    assert(f.sample(230,230)); near(f.m.fundamental_reactive_power,230);
    near(f.m.displacement_angle,45); near(f.m.fundamental_power_factor,std::sqrt(0.5f));
    assert(!f.sample(460,0)); // Completed window does not leak into the next one.
    near(f.m.fundamental_current,2); // Current and THD are still calculated every metering window.
    near(f.m.current_thd,std::sqrt(1.1f*1.1f-1.f)*100,1e-3f);
  }
  {
    Fixture f;
    assert(!f.sample(230,0,200)); assert(f.sample(0,460,800));
    near(f.m.fundamental_reactive_power,368);
    near(f.m.displacement_angle,std::atan2(368.f,46.f)*180.f/3.14159265358979323846f);
    near(f.m.fundamental_power_factor,46.f/std::hypot(46.f,368.f));
  }
  {
    Fixture f; const float a=179.f*3.14159265358979323846f/180.f;
    assert(!f.sample(230*std::cos(a),230*std::sin(a),500));
    assert(f.sample(230*std::cos(a),-230*std::sin(a),500));
    near(std::fabs(f.m.displacement_angle),180); near(f.m.fundamental_power_factor,1);
  }
  {
    Fixture f; assert(!f.sample(230,0,500)); assert(f.sample(-230,0,500));
    near(f.m.fundamental_reactive_power,0);
    assert(std::isnan(f.m.displacement_angle) && std::isnan(f.m.fundamental_power_factor));
    assert(!f.sample(0,0,500)); assert(f.sample(0,0,500));
    near(f.m.fundamental_current,0); near(f.m.fundamental_reactive_power,0);
    assert(std::isnan(f.m.displacement_angle) && std::isnan(f.m.fundamental_power_factor));
    assert(!f.sample(230,0,500)); assert(f.sample(-225,0,500)); // Resultant current <20mA.
    assert(std::isnan(f.m.displacement_angle) && std::isnan(f.m.fundamental_power_factor));
  }
  {
    Fixture f; assert(!f.sample(0,230*0.018f,500)); near(f.m.fundamental_current,0);
    assert(f.sample(0,230*0.024f,500)); // Apply the cutoff to the mean, not each input P/Q.
    near(f.m.fundamental_reactive_power,230*0.021f); near(f.m.displacement_angle,90);
    assert(f.sample(0,230*0.01f,1000)); near(f.m.fundamental_reactive_power,0);
    assert(std::isnan(f.m.displacement_angle) && std::isnan(f.m.fundamental_power_factor));
  }
  {
    Fixture f; assert(!f.sample(230,0,800)); f.component.valid=false;
    assert(f.sample(230,0,200)); assert(!f.m.has_fundamental_analysis);
    f.component.valid=true; assert(!f.sample(0,230,200)); assert(f.sample(0,230,800));
    near(f.m.displacement_angle,90);
    assert(!f.sample(230,0,800)); assert(f.sample(230,0,NAN));
    assert(std::isnan(f.m.fundamental_reactive_power));
    assert(!f.sample(0,230,200)); assert(f.sample(0,230,800)); near(f.m.displacement_angle,90);
  }
  {
    Fixture f; assert(!f.sample(230,0,800)); f.ct.a.calibration=0.025f;
    assert(!f.sample(0,230,200)); assert(f.sample(0,230,800)); near(f.m.displacement_angle,90);
    f.ct.pair=true; assert(!f.sample(230,0,800)); f.ct.b.calibration=0.026f;
    assert(!f.sample(0,230,200)); assert(f.sample(0,230,800)); near(f.m.displacement_angle,90);
    assert(!f.sample(230,0,800)); f.ct.tracker.reset(); // Timeout / line / current-calibration reset.
    assert(!f.sample(0,230,200)); assert(f.sample(0,230,800)); near(f.m.displacement_angle,90);
  }
  for (int output=0;output<3;output++) {
    Fixture f; f.ct.want_reactive=output==0; f.ct.want_factor=output==1; f.ct.want_angle=output==2;
    assert(f.sample(230,230,1000)); // Neither companion entity is required.
    near(f.m.fundamental_reactive_power,230); near(f.m.displacement_angle,45);
    near(f.m.fundamental_power_factor,std::sqrt(0.5f));
  }
  {
    Fixture f; f.ct.tracker.set_interval(0); assert(f.sample(230,230));
    near(f.m.displacement_angle,45); near(f.m.fundamental_power_factor,std::sqrt(0.5f));
    f.frame.transport=MeteringTransport::I2C; assert(f.sample(230,0)); assert(!f.m.has_fundamental_analysis);
    f.ct.want_reactive=f.ct.want_factor=f.ct.want_angle=false; f.ct.tracker.set_interval(1000);
    assert(f.sample(230,0)); // No power-analysis entities: do not accumulate unused analysis.
  }
  {
    MeteringAnalysisTracker t; MeteringAnalysisTracker::Result r; t.set_interval(1000);
    for (float invalid : {NAN,INFINITY,-INFINITY}) {
      assert(t.add_sample(invalid,0,230,100,0.02f,&r)); assert(std::isnan(r.reactive_power));
      assert(t.add_sample(0,invalid,230,100,0.02f,&r));
      assert(t.add_sample(0,0,invalid,100,0.02f,&r));
    }
    assert(t.add_sample(0,0,230,0,0.02f,&r));
    assert(t.add_sample(0,0,0,100,0.02f,&r));
    assert(t.add_sample(0,230,230,1000,0.02f,&r)); near(r.displacement_angle,90);
  }
  {
    RuntimeControls c; MeteringPhaseConfig a,b; MeteringAnalysisTracker::Result r;
    c.analysis_tracker_.set_interval(1000);
    auto begin = [&]() {
      c.pending_analysis_result_valid_=true;
      assert(!c.analysis_tracker_.add_sample(230,0,230,800,0.02f,&r));
    };
    auto after_reset = [&]() {
      assert(!c.pending_analysis_result_valid_);
      assert(!c.analysis_tracker_.add_sample(0,230,230,200,0.02f,&r));
      assert(c.analysis_tracker_.add_sample(0,230,230,800,0.02f,&r)); near(r.displacement_angle,90);
    };
    begin(); c.set_phase(&a); after_reset();
    begin(); c.set_phase(&b); after_reset();
    begin(); c.set_line_pair(&a,&b); after_reset();
    begin(); c.set_current_gain(1.1f); after_reset();
    begin(); c.set_current_phase_correction(1.f); after_reset();
    begin(); c.set_current_gain(1.1f); c.set_current_phase_correction(1.f);
    assert(c.pending_analysis_result_valid_); // Unchanged controls preserve a completed pending result.
    assert(c.analysis_tracker_.add_sample(230,0,230,200,0.02f,&r)); // Unchanged controls do not reset.
  }
  {
    MeteringAnalysisTracker t; MeteringAnalysisTracker::Result r; t.set_interval(3600000);
    const float duration=220.31f;
    const int count=std::ceil(3600000.0/static_cast<double>(duration));
    for (int i=1;i<=count;i++) assert(t.add_sample(230,123.456f,230,duration,0.02f,&r)==(i==count));
    near(r.reactive_power,123.456f); // Long intervals must not accumulate float-duration drift.
  }
  std::puts("PASS analysis interval: shared P/Q, duration weighting, wrap, cancellation, single outputs, resets and defaults");
}
"""
    compile_run(PRELUDE + tracker + measurement + mocks +
                function(METERING, "MeteringAnalysisTracker::add_sample") + "\n".join(methods) + tests)


def test_analysis_schema():
    spec = importlib.util.spec_from_file_location("ev_analysis_test", ROOT / "components/emporiavue/__init__.py")
    component = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(component)
    cv = component.cv
    for value, expected in [("0s",0),("5s",5000),("10s",10000),("60min",3600000)]:
        assert component._validate_analysis_interval(value).total_milliseconds == expected
    for value in ["-1s", "61min", "never", True]:
        try:
            component._validate_analysis_interval(value)
        except cv.Invalid:
            pass
        else:
            raise AssertionError(f"Accepted invalid interval {value}")
    for schema, base in [
        (component.METERING_MAIN_SCHEMA, {"voltage_input":"BLACK","main_clamp":"A","voltage_calibration":0.022}),
        (component.METERING_CIRCUIT_SCHEMA, {"input":"1","line":1}),
        (component.METERING_CT_CLAMP_SCHEMA, {"input":"1","phase_id":"line_a"}),
    ]:
        for value in ["0s","5s"]:
            assert schema({**base,"analysis_interval":value})["analysis_interval"].total_milliseconds in (0,5000)
    for mode, interval, local, valid in [
        ("spi","0s",None,True),("spi","10s","5s",True),("spi","10s","0s",True),
        ("i2c","0s",None,True),("i2c","10s",None,False),("i2c","0s","5s",False),
    ]:
        config = {"mode":mode,"analysis_interval":component._validate_analysis_interval(interval),
                  "mains":{"line_1":{}},"esphome_subdevices":False}
        if local is not None:
            config["circuits"] = {"cir1":{"input":"1","line":1,"analysis_interval":component._validate_analysis_interval(local)}}
        try:
            component._validate_metering_topology(config)
        except cv.Invalid:
            assert not valid, (mode,interval,local)
        else:
            assert valid, (mode,interval,local)
    print("PASS analysis schema: global/local/legacy, defaults, zero override, range and SPI-only validation")


if __name__ == "__main__":
    test_analysis_interval()
    test_analysis_schema()
