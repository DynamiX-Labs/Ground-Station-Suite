#!/usr/bin/env python3
import argparse
import json
import math
import os
import re
from datetime import datetime, timedelta, timezone

BYTES_PER_SAMPLE = {
    "cf32_le": 8,  # complex float32: 2 * 4 bytes
    "cf32_be": 8,
    "ci16_le": 4,  # complex int16: 2 * 2 bytes
    "ci16_be": 4,
    "ci8": 2,  # complex int8: 2 * 1 byte
    "cu8": 2,  # complex uint8: 2 * 1 byte
}


def iso_to_dt(value):
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def dt_to_iso_z(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_user_time(value, recording_start_utc):
    local_tz = datetime.now().astimezone().tzinfo
    if re.match(r"^\d{2}:\d{2}:\d{2}$", value):
        time_part = datetime.strptime(value, "%H:%M:%S").time()
        rec_local_date = recording_start_utc.astimezone(local_tz).date()
        dt_local = datetime.combine(rec_local_date, time_part, tzinfo=local_tz)
        return dt_local.astimezone(timezone.utc)
    if " " in value and "T" not in value:
        value = value.replace(" ", "T")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=local_tz)
    return dt.astimezone(timezone.utc)


def resolve_base_path(input_path):
    if input_path.endswith(".sigmf-data"):
        return input_path[:-11]
    if input_path.endswith(".sigmf-meta"):
        return input_path[:-11]
    return input_path


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def trim_sigmf(args):
    base = resolve_base_path(args.input)
    data_path = f"{base}.sigmf-data"
    meta_path = f"{base}.sigmf-meta"

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found: {data_path}")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"Meta file not found: {meta_path}")

    with open(meta_path, "r", encoding="utf-8") as handle:
        meta = json.load(handle)

    global_meta = meta.get("global", {})
    datatype = global_meta.get("core:datatype")
    sample_rate = float(global_meta.get("core:sample_rate"))
    if datatype not in BYTES_PER_SAMPLE:
        raise ValueError(f"Unsupported datatype: {datatype}")
    bytes_per_sample = BYTES_PER_SAMPLE[datatype]

    recording_start_utc = iso_to_dt(global_meta["gs:start_time"]).astimezone(timezone.utc)

    start_utc = parse_user_time(args.start, recording_start_utc)
    end_utc = parse_user_time(args.end, recording_start_utc)

    if end_utc <= start_utc:
        start_utc, end_utc = end_utc, start_utc
        print("Warning: end time was before start time; swapped them.")

    data_size = os.path.getsize(data_path)
    total_samples = data_size // bytes_per_sample
    duration_seconds = total_samples / sample_rate

    start_offset = (start_utc - recording_start_utc).total_seconds()
    end_offset = (end_utc - recording_start_utc).total_seconds()

    start_offset = clamp(start_offset, 0, duration_seconds)
    end_offset = clamp(end_offset, 0, duration_seconds)

    if end_offset <= start_offset:
        raise ValueError("Trim window is empty after clamping to recording bounds.")

    start_sample = int(math.floor(start_offset * sample_rate))
    end_sample = int(math.ceil(end_offset * sample_rate))
    end_sample = min(end_sample, total_samples)

    if end_sample <= start_sample:
        raise ValueError("Trim window has no samples.")

    new_total_samples = end_sample - start_sample
    new_duration = new_total_samples / sample_rate

    output_base = args.output or f"{base}_trimmed"
    out_data_path = f"{output_base}.sigmf-data"
    out_meta_path = f"{output_base}.sigmf-meta"

    copy_bytes = new_total_samples * bytes_per_sample
    chunk_size = 8 * 1024 * 1024

    with open(data_path, "rb") as src, open(out_data_path, "wb") as dst:
        src.seek(start_sample * bytes_per_sample)
        remaining = copy_bytes
        while remaining > 0:
            chunk = src.read(min(chunk_size, remaining))
            if not chunk:
                break
            dst.write(chunk)
            remaining -= len(chunk)

    new_meta = json.loads(json.dumps(meta))
    new_global = new_meta.get("global", {})
    new_global["gs:start_time"] = dt_to_iso_z(start_utc)
    new_global["gs:finalized_time"] = dt_to_iso_z(start_utc + timedelta(seconds=new_duration))
    new_meta["global"] = new_global

    captures = new_meta.get("captures", [])
    updated_captures = []
    for capture in captures:
        sample_start = int(capture.get("core:sample_start", 0))
        new_sample_start = sample_start - start_sample
        if new_sample_start < 0 or new_sample_start >= new_total_samples:
            continue
        capture["core:sample_start"] = new_sample_start
        if "core:datetime" in capture:
            old_dt = iso_to_dt(capture["core:datetime"]).astimezone(timezone.utc)
            shifted = old_dt - timedelta(seconds=start_offset)
            capture["core:datetime"] = dt_to_iso_z(shifted)
        else:
            capture["core:datetime"] = dt_to_iso_z(
                start_utc + timedelta(seconds=new_sample_start / sample_rate)
            )
        updated_captures.append(capture)

    if not updated_captures:
        updated_captures.append(
            {
                "core:sample_start": 0,
                "core:frequency": captures[0].get("core:frequency") if captures else None,
                "core:datetime": dt_to_iso_z(start_utc),
            }
        )

    new_meta["captures"] = updated_captures

    with open(out_meta_path, "w", encoding="utf-8") as handle:
        json.dump(new_meta, handle, indent=2, sort_keys=False)

    print(f"Trimmed data written to: {out_data_path}")
    print(f"Trimmed meta written to: {out_meta_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Trim a SigMF IQ recording by local/ISO time window."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input .sigmf-data/.sigmf-meta path or base path without extension.",
    )
    parser.add_argument(
        "--start",
        required=True,
        help="Start time (local HH:MM:SS or ISO datetime).",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="End time (local HH:MM:SS or ISO datetime).",
    )
    parser.add_argument(
        "--output",
        help="Output base path without extension (defaults to <input>_trimmed).",
    )
    args = parser.parse_args()
    trim_sigmf(args)


if __name__ == "__main__":
    main()
