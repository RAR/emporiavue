# SAMD09 firmware images

Raw SAMD09 images for flashing through the ESPHome `emporiavue` component.

- `i2c/`: images that use the stock-compatible I2C transport.
- `spi/`: images that use the experimental SPI transport.

The managed firmware packager writes versioned build artifacts here, using names such as `vue2-i2c-v1.0.bin`.
Use raw GitHub URLs from a fixed commit or tag when you want reproducible tests.

## SPI RAM optimization builds

The corrected rebuilds no longer use CPU `WFI`: the main loop polls (emporiavue#9). On a Vue 3, waking from `WFI`
while the DMAC was busy made the CPU execute wrong instruction words, a stale Flash word and, with the wake sequence
in SRAM, the SPI DMA descriptor's first word; both hard-faulted within seconds. Disabling Flash sleep (`CTRLB=0x382`,
the DS80000839B issue 3 workaround) did not prevent it. The SPI frame CRC-32 is computed from a 256-entry table
instead of the DMAC CRC engine, which kept frames ready within their period (same IEEE CRC-32 result on the wire).
The SPI start keeps only the channel-select DMAC accesses inside the interrupt-masked section.
The image versions remain **Vue 2 v1.1** and **Vue 3 v1.2**, so use a fixed commit or SHA-256 to identify the rebuild.
After updating ESPHome, manually press **Flash SAMD Bundled Firmware**; a version-only check cannot identify
an older image with the same version number. Tested on a Vue 3; the Vue 2 image is built from the same source but
was not tested on hardware with this change.

`vue2-spi-v1.1.bin` and `vue3-spi-v1.2.bin` retain all three 1,024-byte SPI frame buffers,
but use two ADC scan buffers instead of the obsolete six-scan history. Delay alignment remains on the ESP32.
An unused internal overrun counter was removed; the transmitted overrun flag is unchanged.
Small CPU-only arrays use their natural element alignment; DMA frames and descriptors retain their required alignment.

Measured with arm-none-eabi GCC 16.1.0 and the repository Makefile (including reserved boot diagnostics):

| Target | Static RAM before | Static RAM after | Remaining RAM for stack |
|---|---:|---:|---:|
| Vue 2 SPI v1.1 | 3,296 B | 3,220 B | 876 B |
| Vue 3 SPI v1.2 | 3,304 B | 3,256 B | 840 B |

Host tests compare two- and six-buffer output byte-for-byte with immediate DMA refill, scan/mux wrap,
UART updates and fault recovery. Sampling configuration and SPI wire format are unchanged.
Remaining RAM is a linker measurement, not a measured worst-case stack margin; hardware validation is still required.

All SAMD09 builds now require at least **800 bytes of stack reserve** after all static RAM, including reserved
boot diagnostics. The linker rejects a smaller reserve, including during incremental builds after linker-script changes.
Run `python3 tools/test_samd09_ram.py` to check the real linker at the boundary and build all three firmware targets.
This regression budget does not replace runtime stack measurements or hardware testing.
