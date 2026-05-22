#!/usr/bin/env python3
"""
Frequency shift a baseband IQ recording to center a signal at a different frequency.

This script reads a sigmf-data file (complex float32), applies frequency translation,
and outputs a new centered baseband file that can be decoded with satdump.

Usage:
    python frequency_shift_baseband.py input.sigmf-data output.sigmf-data --shift_hz -250000

Example:
    # Shift signal from -250kHz offset to center (0 Hz)
    python frequency_shift_baseband.py METEOR.sigmf-data METEOR_centered.sigmf-data --shift_hz -250000
"""

import argparse
import json
import os
import traceback
from pathlib import Path

import numpy as np


def frequency_shift(iq_data, shift_hz, sample_rate):
    """
    Shift the frequency of IQ data by shift_hz.

    Args:
        iq_data: Complex numpy array of IQ samples
        shift_hz: Frequency shift in Hz (negative shifts down, positive shifts up)
        sample_rate: Sample rate in Hz

    Returns:
        Frequency-shifted IQ data
    """
    # Generate time array
    t = np.arange(len(iq_data)) / sample_rate

    # Create complex exponential for frequency shift
    # To shift by -250kHz, multiply by e^(j*2*pi*250000*t)
    shift_signal = np.exp(1j * 2 * np.pi * shift_hz * t)

    # Apply frequency shift
    shifted_data = iq_data * shift_signal

    return shifted_data


def process_baseband_file(input_file, output_file, shift_hz, chunk_size=10_000_000):
    """
    Process a baseband file in chunks to avoid memory issues.

    Args:
        input_file: Path to input .sigmf-data file
        output_file: Path to output .sigmf-data file
        shift_hz: Frequency shift in Hz
        chunk_size: Number of samples to process at a time
    """
    # Read metadata from .sigmf-meta file
    input_meta_file = Path(str(input_file).replace(".sigmf-data", ".sigmf-meta"))
    if not input_meta_file.exists():
        raise FileNotFoundError(f"Metadata file not found: {input_meta_file}")

    with open(input_meta_file, "r") as f:
        meta = json.load(f)

    sample_rate = meta["global"]["core:sample_rate"]
    datatype = meta["global"]["core:datatype"]

    print(f"Input file: {input_file}")
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Data type: {datatype}")
    print(f"Frequency shift: {shift_hz} Hz ({shift_hz/1e3:.1f} kHz)")

    if datatype != "cf32_le":
        raise ValueError(f"Unsupported data type: {datatype}. Expected cf32_le (complex float32)")

    # Get file size
    file_size = os.path.getsize(input_file)
    num_samples = file_size // 8  # cf32 = 2 floats * 4 bytes each = 8 bytes per sample
    print(f"Total samples: {num_samples:,}")
    print(f"File size: {file_size / (1024**3):.2f} GB")

    # Process in chunks
    with open(input_file, "rb") as fin, open(output_file, "wb") as fout:
        sample_offset = 0
        chunk_num = 0
        # Track phase to maintain continuity across chunks
        phase = 0.0

        while sample_offset < num_samples:
            # Calculate chunk size (last chunk might be smaller)
            current_chunk_size = min(chunk_size, num_samples - sample_offset)

            # Read chunk
            print(
                f"\rProcessing chunk {chunk_num + 1} ({sample_offset:,}/{num_samples:,} samples, "
                f"{100*sample_offset/num_samples:.1f}%)",
                end="",
                flush=True,
            )

            iq_chunk = np.fromfile(fin, dtype=np.complex64, count=current_chunk_size)

            # Check for corrupted input data
            if not np.all(np.isfinite(iq_chunk)):
                raise ValueError(
                    f"Input file contains invalid values (inf/nan) at chunk {chunk_num}. "
                    f"The input recording is corrupted."
                )

            # Apply frequency shift with phase continuity
            # Use relative time within chunk to avoid numerical overflow
            t = np.arange(current_chunk_size, dtype=np.float64) / sample_rate
            # Use cos/sin instead of exp to handle large phase arguments better
            arg = 2 * np.pi * shift_hz * t + phase
            shift_signal = np.cos(arg) + 1j * np.sin(arg)
            # Ensure result stays complex64 to match input dtype
            shifted_chunk = (iq_chunk * shift_signal).astype(np.complex64)

            # Verify output is valid before writing
            if not np.all(np.isfinite(shifted_chunk)):
                raise ValueError(
                    f"Frequency shift produced invalid values (inf/nan) at chunk {chunk_num}. "
                    f"This may indicate input data corruption or numerical overflow."
                )

            # Update phase for next chunk (wrap to keep it bounded)
            phase = (phase + 2 * np.pi * shift_hz * current_chunk_size / sample_rate) % (2 * np.pi)

            # Write shifted chunk
            shifted_chunk.astype(np.complex64).tofile(fout)

            sample_offset += current_chunk_size
            chunk_num += 1

    print(f"\rProcessing complete! Processed {num_samples:,} samples in {chunk_num} chunks")
    print(f"Output file: {output_file}")

    # Create output metadata file
    output_meta_file = Path(str(output_file).replace(".sigmf-data", ".sigmf-meta"))

    # Update frequency in metadata
    # The new center frequency should be where the signal was originally located
    # For example: recording at 138.15 MHz with signal at 137.9 MHz (-250 kHz offset)
    # After shifting by +250 kHz, the signal is now centered, so new center = 137.9 MHz
    output_meta = meta.copy()
    if "captures" in output_meta and len(output_meta["captures"]) > 0:
        original_freq = output_meta["captures"][0]["core:frequency"]
        # The signal was at (original_freq + offset from center)
        # After shifting to center it, the new center frequency is where the signal was
        signal_freq = original_freq - shift_hz  # Original signal location
        output_meta["captures"][0]["core:frequency"] = signal_freq
        print(f"Updated center frequency: {original_freq/1e6:.3f} MHz -> {signal_freq/1e6:.3f} MHz")
        print(f"Signal was at {signal_freq/1e6:.3f} MHz, now centered in baseband")

    # Add processing note
    if "annotations" not in output_meta:
        output_meta["annotations"] = []
    output_meta["annotations"].append(
        {
            "core:sample_start": 0,
            "core:sample_count": num_samples,
            "core:comment": f"Frequency shifted by {shift_hz} Hz using frequency_shift_baseband.py",
        }
    )

    with open(output_meta_file, "w") as f:
        json.dump(output_meta, f, indent=2)

    print(f"Created metadata file: {output_meta_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Frequency shift baseband IQ recordings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Shift signal from -250kHz to center (signal at 137.9 MHz, recording at 138.15 MHz)
  %(prog)s METEOR.sigmf-data METEOR_centered.sigmf-data --shift_hz 250000

  # The shift_hz should be POSITIVE to move signal from negative offset to center
  # If signal is at -250 kHz, use +250000 to center it
        """,
    )

    parser.add_argument("input_file", help="Input .sigmf-data file")
    parser.add_argument("output_file", help="Output .sigmf-data file")
    parser.add_argument(
        "--shift_hz",
        type=float,
        required=True,
        help="Frequency shift in Hz (positive to shift up, negative to shift down)",
    )
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=10_000_000,
        help="Number of samples to process at once (default: 10M)",
    )

    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}")
        return 1

    # Process the file
    try:
        process_baseband_file(args.input_file, args.output_file, args.shift_hz, args.chunk_size)
        print("\nSuccess! You can now decode with satdump:")
        print(
            f"  satdump meteor_m2-x_lrpt baseband {args.output_file} output_dir --samplerate 1e6 --baseband_format cf32 --dc_block"
        )
    except Exception as e:
        print(f"\nError: {e}")
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
