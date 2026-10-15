#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 rosenrot00 and contributors
"""Accepted-frame callback contract, using the production API and submit method."""

from test_esphome_metering import HEADER, METERING, PRELUDE, compile_run, function


def test_frame_callback():
    structs = HEADER[HEADER.index("  struct MeteringPhase {"):HEADER.index("  static_assert(sizeof(MeteringPhase)")]
    api_start = HEADER.index("  template<typename F> void add_on_frame_callback(")
    api_end = HEADER.index("\n  }", api_start) + len("\n  }")
    api = HEADER[api_start:api_end]
    submit = function(METERING, "EmporiaVueComponent::submit_metering_frame_")
    fixture = r"""
class EmporiaVueComponent { public:
""" + structs.replace("protected:", "public:") + api + r"""
  CallbackManager<void(const MeteringFrame &)> frame_callbacks_;
  uint32_t metering_timeout_ms_{2000},last_metering_frame_ms_{0},last_metering_acquisition_epoch_{0};
  uint32_t last_metering_sequence_{0},i2c_missing_readings_window_{0};
  bool metering_data_stale_{true},last_metering_sequence_valid_{false};
  MeteringTransport last_metering_transport_{MeteringTransport::UNKNOWN};
  unsigned published{0},aggregated{0},invalidations{0};
  void invalidate_metering_(uint32_t) {++invalidations;}
  void publish_metering_frame_(const MeteringFrame &,bool publish) {++aggregated; published+=publish;}
  void submit_metering_frame_(const MeteringFrame &,bool);
};
"""
    tests = r"""
int main() {
  using Frame=EmporiaVueComponent::MeteringFrame;
  static_assert(sizeof(Frame)==752);
  for(auto transport:{MeteringTransport::I2C,MeteringTransport::SPI}) {
    EmporiaVueComponent c;
    Frame frame; frame.valid=true; frame.transport=transport;
    simulated_ms=5000; frame.timestamp_ms=4900; frame.duration_ms=220;
    frame.sequence=1; frame.acquisition_epoch=7;
    c.submit_metering_frame_(frame,false); // Empty callback manager is harmless.
    assert(c.aggregated==1 && c.published==0);
    unsigned calls=0,second_calls=0;
    c.add_on_frame_callback([&](const Frame &received) {
      assert(&received==&frame); // Reference, not a frame copy.
      assert(c.aggregated==1+calls); // Hook precedes aggregation.
      assert(received.transport==transport && received.duration_ms==220);
      assert(received.acquisition_epoch==frame.acquisition_epoch);
      assert(received.timestamp_ms==4900); // Acquisition time, not delivery time.
      assert(c.last_metering_sequence_==received.sequence);
      ++calls;
    });
    c.add_on_frame_callback([&](const Frame &) {assert(calls==second_calls+1);++second_calls;});
    ++frame.sequence; c.submit_metering_frame_(frame,false);
    ++frame.sequence; c.submit_metering_frame_(frame,true);
    assert(calls==2 && second_calls==2 && c.published==1 && c.aggregated==3);
    frame.valid=false; c.submit_metering_frame_(frame,true);
    frame.valid=true; simulated_ms=8000; c.submit_metering_frame_(frame,true);
    assert(calls==2 && second_calls==2 && c.aggregated==3); // Invalid/expired rejected.
    simulated_ms=5000; frame.sequence+=2; ++frame.acquisition_epoch;
    c.submit_metering_frame_(frame,false); // Accepted gap/restart still delivered with metadata.
    assert(calls==3 && second_calls==3 && c.aggregated==4);
  }
  std::puts("PASS frame hook: I2C/SPI, no listener, multiple listeners, const reference, ordering, freshness and queued windows");
}
"""
    compile_run(PRELUDE + fixture + submit + tests)


if __name__ == "__main__":
    test_frame_callback()
