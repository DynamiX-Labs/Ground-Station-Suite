#!/usr/bin/env python3
import argparse
import json
import math
import os
from typing import Any, Dict

import numpy as np


def _update_meta(meta_in_path: str, meta_out_path: str, shift_hz: float) -> None:
    with open(meta_in_path, "r", encoding="utf-8") as f:
        meta: Dict[str, Any] = json.load(f)

    captures = meta.get("captures", [])
    for cap in captures:
        if "core:frequency" in cap:
            cap["core:frequency"] = float(cap["core:frequency"]) + shift_hz

    desc = meta.get("global", {}).get("core:description", "")
    note = f" (freq_shift {shift_hz} Hz applied)"
    if isinstance(desc, str) and note not in desc:
        meta.setdefault("global", {})["core:description"] = desc + note

    with open(meta_out_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=False)
        f.write("\n")


def shift_iq(
    in_path: str, out_path: str, sample_rate: float, shift_hz: float, chunk_samples: int
) -> None:
    phase_inc = 2.0 * math.pi * shift_hz / sample_rate
    sample_offset = 0

    with open(in_path, "rb") as fin, open(out_path, "wb") as fout:
        while True:
            data = np.fromfile(fin, dtype=np.complex64, count=chunk_samples)
            if data.size == 0:
                break
            n = data.size
            phases = phase_inc * (sample_offset + np.arange(n, dtype=np.float64))
            rotator = np.exp(1j * phases).astype(np.complex64)
            shifted = data * rotator
            shifted.tofile(fout)
            sample_offset += n


def main() -> None:
    parser = argparse.ArgumentParser(description="Frequency shift a SigMF IQ recording (cf32_le).")
    parser.add_argument("input", help="Input .sigmf-data path")
    parser.add_argument("output", help="Output .sigmf-data path")
    parser.add_argument(
        "--samplerate", type=float, required=True, help="Sample rate in Hz (e.g. 4e6)"
    )
    parser.add_argument(
        "--shift",
        type=float,
        required=True,
        help="Frequency shift in Hz (positive shifts signal to the right)",
    )
    parser.add_argument(
        "--chunk",
        type=int,
        default=1_000_000,
        help="Samples per chunk (default: 1,000,000)",
    )
    args = parser.parse_args()

    shift_iq(args.input, args.output, args.samplerate, args.shift, args.chunk)

    meta_in = os.path.splitext(args.input)[0] + ".sigmf-meta"
    meta_out = os.path.splitext(args.output)[0] + ".sigmf-meta"
    if os.path.exists(meta_in):
        _update_meta(meta_in, meta_out, args.shift)


if __name__ == "__main__":
    main()
