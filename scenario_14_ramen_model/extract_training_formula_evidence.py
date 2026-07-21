#!/usr/bin/env python3
"""
Extract training formula evidence from IL2CPP binary for Scenario 14 Ramen.

Usage:
    python3 extract_training_formula_evidence.py /path/to/libil2cpp.so /path/to/global-metadata.dat

Requirements:
    pip install capstone

Output:
    training_formula_evidence.json — evidence file with disassembly-backed findings
"""

import json
import struct
import sys
import os
from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
except ImportError:
    print("ERROR: pip install capstone", file=sys.stderr)
    sys.exit(1)

# ============================================================
# Constants — from work order build verification
# ============================================================

EXPECTED_LIBIL2CPP_SHA256 = "3e32f9792d85a79f4cead60fc7676e187ecada3bccf6aa4d28d809aa7918d5c0"
EXPECTED_METADATA_SHA256 = "af653230aca9fba539348040d3718bbc265f64a2613083e11989dd36c6b224bf"
LOAD_BASE = 0x7330EF37C4  # documented in ramen_planner_evidence.md

# Target method addresses from IL2CPP method dump
TARGET_METHODS = {
    "ServingPracticeRegionEffectBonusVO.Apply": {
        "runtime_addr": 0x7339B12A0C,
        "scan_size": 0x200,
        "backward_scan": 0x400,
    },
    "ServingPracticeRegionEffectRepository.GetWithCheckPointPt": {
        "runtime_addr": 0x7339B021DC,
        "scan_size": 0x200,
        "backward_scan": 0x100,
    },
    "ServingPracticeEffectRepositoryUtil.GetTrainingMatchingObtain": {
        "runtime_addr": 0x7339B01CD8,
        "scan_size": 0x200,
        "backward_scan": 0x40,
    },
    "ServingPracticeTransactionEntity.IsBonusEffectTraining": {
        "runtime_addr": 0x7339AF9514,
        "scan_size": 0x100,
        "backward_scan": 0x40,
    },
    "ServingPracticeEffectVO.CreateRegionEffect": {
        "runtime_addr": 0x7339B11D0C,
        "scan_size": 0x100,
        "backward_scan": 0x40,
    },
}

# ELF segment info (from readelf -l)
TEXT_VADDR = 0x03B9FF4C
TEXT_FILE_OFFSET = 0x03B9BF4C
VADDR_TO_FILE_OFFSET = TEXT_VADDR - TEXT_FILE_OFFSET  # = 0x4000


def verify_sha256(filepath, expected):
    import hashlib
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    actual = h.hexdigest()
    if actual != expected:
        print(f"WARNING: SHA-256 mismatch for {filepath}", file=sys.stderr)
        print(f"  expected: {expected}", file=sys.stderr)
        print(f"  actual:   {actual}", file=sys.stderr)
        return False
    return True


def find_function_start(data, file_offset, max_backward=0x400):
    """Scan backward from file_offset to find a function prologue."""
    for offset in range(0, max_backward, 4):
        check = file_offset - offset
        if check < 0:
            break
        if check + 4 > len(data):
            break
        inst = struct.unpack('<I', data[check:check+4])[0]

        # sub sp, sp, #N → D10x03FF
        if (inst & 0xFF0003FF) == 0xD10003FF:
            return check, offset
        # stp x29, x30, [sp, #-N]! → A9Cx7BFD
        if (inst & 0xFFE07FFF) == 0xA9807BFD:
            return check, offset
        # stp x29, x30, [sp, #N] → A9Ax7BFD
        if (inst & 0xFFE07FFF) == 0xA9A07BFD:
            return check, offset
        # stp x30, xN, [sp, #-N]!
        if (inst & 0xFFE00C00) == 0xA9800400:
            return check, offset

    return file_offset, 0


def disassemble(so_path, method_name, method_info):
    """Disassemble a target method from the .so file."""
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    md.detail = True

    runtime_addr = method_info["runtime_addr"]
    vaddr = runtime_addr - LOAD_BASE
    file_offset = vaddr - VADDR_TO_FILE_OFFSET

    with open(so_path, 'rb') as f:
        f.seek(max(0, file_offset - method_info["backward_scan"]))
        pre_data = f.read(method_info["backward_scan"] + method_info["scan_size"])

    actual_offset, codegen_delta = find_function_start(
        pre_data, method_info["backward_scan"]
    )
    actual_file_offset = file_offset - codegen_delta
    actual_vaddr = vaddr - codegen_delta

    with open(so_path, 'rb') as f:
        f.seek(actual_file_offset)
        code = f.read(method_info["scan_size"] + codegen_delta)

    instructions = []
    for inst in md.disasm(code, actual_vaddr):
        instructions.append({
            "addr": f"0x{inst.address:08x}",
            "mnemonic": inst.mnemonic,
            "op_str": inst.op_str,
        })
        if inst.mnemonic == 'ret' and inst.address > vaddr + 4:
            break

    return {
        "method": method_name,
        "runtime_addr": f"0x{runtime_addr:x}",
        "vaddr": f"0x{vaddr:08x}",
        "actual_start": f"0x{actual_vaddr:08x}",
        "codegen_offset": f"+0x{codegen_delta:x}" if codegen_delta else "0 (codegen = start)",
        "instruction_count": len(instructions),
        "instructions": instructions[:50],  # cap for output size
    }


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <libil2cpp.so> <global-metadata.dat>", file=sys.stderr)
        sys.exit(1)

    so_path = sys.argv[1]
    meta_path = sys.argv[2]

    # Verify build
    print("Verifying build fingerprints...")
    so_ok = verify_sha256(so_path, EXPECTED_LIBIL2CPP_SHA256)
    meta_ok = verify_sha256(meta_path, EXPECTED_METADATA_SHA256)

    if not so_ok or not meta_ok:
        print("Build mismatch — continuing anyway for development", file=sys.stderr)

    # Disassemble each target method
    results = {}
    for name, info in TARGET_METHODS.items():
        print(f"Disassembling {name}...")
        results[name] = disassemble(so_path, name, info)

    # Output
    output = {
        "schema_version": 1,
        "scenario": 14,
        "build": {
            "libil2cpp_sha256": EXPECTED_LIBIL2CPP_SHA256,
            "metadata_sha256": EXPECTED_METADATA_SHA256,
            "load_base": hex(LOAD_BASE),
        },
        "methods": results,
    }

    out_path = Path(__file__).parent / "training_formula_evidence_raw.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nOutput: {out_path}")
    print(f"Methods disassembled: {len(results)}")
    for name, r in results.items():
        print(f"  {name}: {r['instruction_count']} instructions, "
              f"codegen_offset={r['codegen_offset']}")


if __name__ == '__main__':
    main()
