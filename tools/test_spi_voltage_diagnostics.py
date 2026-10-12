#!/usr/bin/env python3
"""Test real SPI validation, Vue 3 UART metadata and optional SPI diagnostic entities."""

import importlib.util
import re

from test_esphome_metering import HEADER, PRELUDE, ROOT, SPI, compile_run, component_fields, function


def test_voltage_metadata():
    methods = ["validate_spi_frame_", "decode_spi_voltage_diagnostics_", "get_spi_voltage_diagnostics_",
               "publish_spi_voltage_diagnostics_", "process_spi_frame_"]
    bodies = [function(SPI, "EmporiaVueComponent::" + name) for name in methods]
    declarations = [body[:body.index("{")].replace("EmporiaVueComponent::", "").rstrip() + ";"
                    for body in bodies]
    structs = HEADER[HEADER.index("  struct SpiQueuedFrame {"):HEADER.index("  struct SpiFundamentalSample {")]
    structs = structs.replace("#endif", "")
    fields = component_fields(*bodies)
    size = re.search(r"^static constexpr uint16_t SPI_RAW_FRAME_SIZE[^\n]*;", HEADER, re.M).group()
    helpers = SPI[SPI.index("static constexpr uint8_t SPI_VUE2_RAW_FRAME_VERSION"):
                  SPI.index("void EmporiaVueComponent::publish_spi_diagnostics_")]
    mocks = r"""
using portMUX_TYPE = int;
#define USE_ESP32
#define portMUX_INITIALIZER_UNLOCKED 0
#define portENTER_CRITICAL(...) ((void)0)
#define portEXIT_CRITICAL(...) ((void)0)
namespace sensor {
struct Sensor {
  float state{NAN}; unsigned count{0};
  void publish_state(float value) {state=value; ++count;}
};
}
"""
    extra = r"""
  unsigned decoded{0}, resets{0};
  void decode_spi_raw_frame_(const uint8_t*,uint32_t,uint32_t,uint32_t) {++decoded;}
  void reset_spi_metering_state_() {++resets;}
"""
    tests = r"""
void crc(uint8_t *data) {
  uint32_t value=UINT32_MAX;
  for (unsigned byte=0;byte<1020;++byte) {
    value^=data[byte];
    for (unsigned bit=0;bit<8;++bit) value=(value>>1)^((value&1) ? 0xEDB88320U : 0);
  }
  value=~value;
  for (unsigned byte=0;byte<4;++byte) data[1020+byte]=value>>(byte*8);
}
void word(uint8_t *data,unsigned index,uint32_t value) {
  for (unsigned byte=0;byte<4;++byte) data[12+(index+byte)*18+17]=value>>(byte*8);
}
int main() {
  using Error=EmporiaVueComponent::SpiFrameValidationError;
  EmporiaVueComponent c; c.hardware_id_=3;
  sensor::Sensor accepted, errors, rejected, age;
  c.diag_voltage_telegrams_sensor_=&accepted;
  c.diag_voltage_uart_errors_sensor_=&errors;
  c.diag_voltage_rejected_telegrams_sensor_=&rejected;
  c.diag_voltage_age_sensor_=&age;
  c.publish_spi_voltage_diagnostics_();
  assert(std::isnan(accepted.state) && std::isnan(errors.state) && std::isnan(rejected.state));
  assert(std::isnan(age.state));
  EmporiaVueComponent::SpiQueuedFrame frame; frame.trans_len_bits=8192;
  auto data=frame.data;
  data[0]=2; data[1]=2; data[2]=0xF0; data[3]=3;
  data[6]=(816U<<3)&255; data[7]=(816U<<3)>>8;
  crc(data); c.process_spi_frame_(frame); c.publish_spi_voltage_diagnostics_();
  assert(c.decoded==1 && !c.spi_voltage_diagnostics_.available); // Old zero-reserved firmware.
  assert(std::isnan(accepted.state) && std::isnan(age.state));
  word(data,0,0xF1234567); word(data,4,13); word(data,8,29); word(data,12,1000);
  word(data,16,0x44555645); data[12+20*18+17]=1;
  crc(data); c.process_spi_frame_(frame); c.publish_spi_voltage_diagnostics_();
  assert(c.spi_voltage_diagnostics_.available && c.spi_voltage_diagnostics_.voltage_valid);
  assert(c.spi_voltage_diagnostics_.accepted_telegrams==0xF1234567);
  assert(accepted.state==float(0xF1234567) && errors.state==13 && rejected.state==29);
  assert(std::abs(age.state-51.0f)<0.0001f);
  // All reserved bytes are CRC-protected; corruption must not replace a good snapshot.
  word(data,4,99); c.process_spi_frame_(frame); c.publish_spi_voltage_diagnostics_();
  assert(c.validate_spi_frame_(data,8192).error==Error::CRC_MISMATCH);
  assert(errors.state==13 && c.spi_voltage_diagnostics_.uart_errors==13);
  crc(data); c.process_spi_frame_(frame); assert(c.spi_voltage_diagnostics_.uart_errors==99);
  // No version guessing: unknown marker/version is unavailable, never a false zero.
  data[12+20*18+17]=2; crc(data); c.process_spi_frame_(frame);
  c.publish_spi_voltage_diagnostics_(); assert(std::isnan(accepted.state));
  data[12+20*18+17]=1; word(data,16,0); crc(data); c.process_spi_frame_(frame);
  assert(!c.spi_voltage_diagnostics_.available);
  word(data,16,0x44555645); word(data,0,0); word(data,4,0); word(data,8,0); word(data,12,0);
  data[6]|=4; crc(data); c.process_spi_frame_(frame); c.publish_spi_voltage_diagnostics_();
  assert(accepted.state==0 && errors.state==0 && rejected.state==0 && std::isnan(age.state));
  // A reset/wrap is exposed as a new raw counter, not unsigned-delta inflation.
  data[6]&=~4U; crc(data); c.process_spi_frame_(frame); c.publish_spi_voltage_diagnostics_();
  assert(accepted.state==0 && age.state==0); // Count zero may also be a 32-bit wrap.
  word(data,0,UINT32_MAX); word(data,12,UINT32_MAX); crc(data);
  c.process_spi_frame_(frame); c.publish_spi_voltage_diagnostics_();
  assert(std::isfinite(age.state) && age.state>2.0e8f);
  // Even a matching EVUD marker never applies to Vue 2 frames.
  c.hardware_id_=2; data[0]=1; data[1]=1; word(data,0,632); crc(data);
  c.process_spi_frame_(frame); c.publish_spi_voltage_diagnostics_();
  assert(!c.spi_voltage_diagnostics_.available && std::isnan(errors.state));
  auto validation=c.validate_spi_frame_(data,8192);
  assert(!c.decode_spi_voltage_diagnostics_(nullptr,validation,3).available);
  std::puts("PASS Vue 3 voltage diagnostics: CRC, EVUD compatibility, raw reset/wrap, validity and milliseconds");
}
"""
    compile_run(PRELUDE + mocks + size + helpers + "\nclass EmporiaVueComponent {public:\n" +
                structs + fields + extra + "\n".join(declarations) + "\n};\n" + "\n".join(bodies) + tests)


def test_voltage_diagnostic_config():
    spec = importlib.util.spec_from_file_location("ev_voltage_test", ROOT / "components/emporiavue/__init__.py")
    component = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(component)
    keys = set(component.VUE3_SPI_DIAGNOSTIC_ENTITY_NAMES)
    for hardware in ("vue2", "vue3", "custom"):
        for mode in ("spi", "i2c"):
            for enabled in (False, True):
                config = {"hardware": hardware, "mode": mode}
                if enabled:
                    config["diagnostics_interval"] = "10s"
                defaults = component._apply_diagnostics_defaults(config)
                assert keys.intersection(defaults) == (keys if enabled and hardware == "vue3" and mode == "spi" else set())
    for key, name in component.VUE3_SPI_DIAGNOSTIC_ENTITY_NAMES.items():
        validator = next(value for marker, value in component.EMPORIAVUE_SCHEMA.schema.items()
                         if marker.schema == key)
        config = validator({"name": name})
        assert config["entity_category"] == "diagnostic"
        assert config["state_class"] == "measurement"
        if key == "diag_voltage_age":
            assert config["unit_of_measurement"] == "ms"
        else:
            assert config["accuracy_decimals"] == 0
    print("PASS Vue 3 diagnostic config: opt-in defaults, sensor schema and milliseconds")


def test_metering_journal_diagnostic():
    publisher = function(SPI, "EmporiaVueComponent::publish_spi_diagnostics_")
    block = re.search(r"  if \(this->diag_spi_metering_window_drops_sensor_ != nullptr\) \{.*?\n  \}",
                      publisher, re.S).group()
    fields = component_fields(block)
    mocks = r"""
namespace sensor {
struct Sensor {float state{NAN}; unsigned calls{0}; void publish_state(float s) {state=s; ++calls;}};
}
"""
    test = r"""
int main() {
  EmporiaVueComponent c; c.publish(); // Optional entity, no null access.
  sensor::Sensor sensor; c.diag_spi_metering_window_drops_sensor_=&sensor;
  c.publish(); assert(sensor.state==0 && sensor.calls==1);
  c.spi_metering_window_drops_=7; c.spi_metering_stale_windows_=11;
  c.publish(); assert(sensor.state==18 && sensor.calls==2);
  c.spi_metering_window_drops_=0; c.spi_metering_stale_windows_=0;
  c.publish(); assert(sensor.state==0 && sensor.calls==3);
  std::puts("PASS SPI journal diagnostic: optional entity, queue-full plus stale-window sum and reset");
}
"""
    compile_run(PRELUDE + mocks + "class EmporiaVueComponent {public:\n" + fields +
                "\nvoid publish() {\n" + block + "\n}\n};\n" + test)
    spec = importlib.util.spec_from_file_location("ev_journal_test", ROOT / "components/emporiavue/__init__.py")
    component = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(component)
    key = "diag_spi_metering_window_drops"
    assert component.SPI_RUNTIME_DIAGNOSTIC_ENTITY_NAMES[key] == "ESP SPI Metering Window Drops"
    for hardware in ("vue2", "vue3", "custom"):
        for mode in ("spi", "i2c"):
            for enabled in (False, True):
                config = {"hardware": hardware, "mode": mode}
                if enabled:
                    config["diagnostics_interval"] = "10s"
                assert (key in component._apply_diagnostics_defaults(config)) == (enabled and mode == "spi")
    validator = next(value for marker, value in component.EMPORIAVUE_SCHEMA.schema.items() if marker.schema == key)
    config = validator({"name": "ESP SPI Metering Window Drops"})
    assert config["entity_category"] == "diagnostic" and config["accuracy_decimals"] == 0
    print("PASS SPI journal config: SPI-only automatic diagnostics and independent sensor schema")


if __name__ == "__main__":
    test_voltage_metadata()
    test_voltage_diagnostic_config()
    test_metering_journal_diagnostic()
