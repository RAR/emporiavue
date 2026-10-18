#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 rosenrot00 and contributors
"""Exercise the production SAMD09 linker RAM guard and build all firmware targets.

Run: python3 tools/test_samd09_ram.py
Requires make and the arm-none-eabi GCC/binutils toolchain. Outputs stay temporary.
The 800-byte limit is a static RAM budget, not a proof of runtime stack safety.
"""

from pathlib import Path
import os
import re
import shlex
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "firmware/samd09"
LINKER = FIRMWARE / "samd09d14.ld"
MINIMUM_RESERVE = 800
RAM_SIZE = 4096
CC = shlex.split(os.environ.get("ARM_CC", "arm-none-eabi-gcc"))
NM = shlex.split(os.environ.get("ARM_NM", "arm-none-eabi-nm"))
OBJDUMP = shlex.split(os.environ.get("ARM_OBJDUMP", "arm-none-eabi-objdump"))
OBJCOPY = shlex.split(os.environ.get("ARM_OBJCOPY", "arm-none-eabi-objcopy"))


def run(command, **kwargs):
    return subprocess.run(command, text=True, capture_output=True, **kwargs)


def symbols(elf):
    result = run([*NM, "-n", str(elf)], check=True)
    return {parts[-1]: int(parts[0], 16) for line in result.stdout.splitlines()
            if len(parts := line.split()) >= 3 and parts[0] != "U"}


def test_linker_boundary(folder):
    # Include reserved and initialized data, so a check of .bss size alone
    # cannot accidentally pass. The production linker must account for all RAM.
    for reserve in (804, 800, 796, 792):
        static_bss = RAM_SIZE - reserve - 32 - 4
        source = f"""
volatile unsigned char boot[32] __attribute__((section(".bss.$RESERVED")));
volatile unsigned int initialized = 1;
volatile unsigned char storage[{static_bss}];
void irq_handler_reset(void) {{
    for (;;) storage[0] = boot[0] + initialized;
}}
"""
        obj, elf = folder / f"boundary-{reserve}.o", folder / f"boundary-{reserve}.elf"
        run([*CC, "-std=gnu99", "-Os", "-ffreestanding", "-fdata-sections", "-ffunction-sections",
             "-mcpu=cortex-m0plus", "-mthumb", "-x", "c", "-c", "-", "-o", str(obj)],
            input=source, check=True)
        result = run([*CC, "-mcpu=cortex-m0plus", "-mthumb", "-nostartfiles", "-nodefaultlibs",
                      f"-Wl,--script={LINKER},--gc-sections", str(obj), "-o", str(elf)])
        if reserve >= MINIMUM_RESERVE:
            assert result.returncode == 0, result.stderr
            values = symbols(elf)
            assert values["__top_ram"] - values["_ebss"] == reserve
            assert values["_edata"] - values["_data"] == 4
            print(f"PASS linker: {reserve} bytes reserve accepted (reserved + data + bss counted)")
        else:
            assert result.returncode != 0, "Linker accepted less than 800 bytes reserve"
            assert "SAMD09 requires at least 800 bytes of stack reserve" in result.stderr, result.stderr
            print(f"PASS linker: {reserve} bytes reserve rejected by production ASSERT")


def test_firmware_builds(folder):
    for source in ("main.c", "main_spi.c", "main_spi_vue3.c"):
        build = folder / Path(source).stem
        command = ["make", "-C", str(FIRMWARE), f"BUILD={build}", f"SOURCE={source}",
                   f"CC={shlex.join(CC)}"]
        result = run(command)
        assert result.returncode == 0, result.stdout + result.stderr
        elf = build / "EmporiaSamd09.elf"
        values = symbols(elf)
        reserve = values["__top_ram"] - values["_ebss"]
        assert reserve >= MINIMUM_RESERVE, f"{source}: only {reserve} bytes reserve"
        print(f"PASS {source}: {RAM_SIZE - reserve} bytes static RAM, {reserve} bytes reserve")
        test_ram_wake_code(elf, values, build, source != "main.c")
        # A changed linker script must trigger relinking even in an incremental
        # build. -W is a dry-run simulation; the repository file is not touched.
        relink = run([*command, "-n", "-W", "samd09d14.ld"], check=True)
        assert "--script=./samd09d14.ld" in relink.stdout, "Linker script is not a build dependency"
        print(f"PASS {source}: linker-script changes trigger relinking")


def test_ram_wake_code(elf, values, build, spi):
    # Vue 3 must never execute WFI (emporiavue#9): after waking with the DMAC busy the
    # CPU fetched wrong instruction words, from Flash and even from SRAM. The SPI
    # builds therefore poll; nothing runs from SRAM and no WFI instruction is linked.
    name = "sleep_and_restore_interrupts_from_ram"
    assert values["_ramfunc_start"] == values["_ramfunc_end"]
    assert name not in values
    if spi:
        disassembly = run([*OBJDUMP, "-d", str(elf)], check=True).stdout
        assert not re.search(r"\twfi\s*$", disassembly, re.M), "SPI firmware must not contain WFI"


def main():
    with tempfile.TemporaryDirectory(prefix="samd09-ram-tests-") as directory:
        folder = Path(directory)
        test_linker_boundary(folder)
        test_firmware_builds(folder)


if __name__ == "__main__":
    main()
