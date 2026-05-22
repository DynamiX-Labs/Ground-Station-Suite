from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (BACKEND_ROOT / rel_path).read_text(encoding="utf-8")


def test_workers_emit_logical_center_contract_fields():
    worker_files = [
        "workers/rtlsdrworker.py",
        "workers/soapysdrlocalworker.py",
        "workers/soapysdrremoteworker.py",
        "workers/uhdworker.py",
    ]

    for rel_path in worker_files:
        source = _read(rel_path)
        assert '"center_freq": logical_center_freq' in source
        assert '"logical_center_freq_hz": logical_center_freq' in source
        assert '"rf_center_freq_hz":' in source
        assert '"offset_freq_hz": offset_freq' in source
        assert '"dsp_shift_hz":' in source


def test_demodulators_prefer_logical_center_freq_when_present():
    demod_files = [
        "demodulators/ssbdemodulator.py",
        "demodulators/amdemodulator.py",
        "demodulators/fmdemodulator.py",
        "demodulators/fmstereodemodulator.py",
        "demodulators/bpskdecoder.py",
        "demodulators/fskdecoder.py",
        "demodulators/sstvdecoder.py",
        "demodulators/loradecoder.py",
        "demodulators/iqrecorder.py",
    ]
    contract_snippet = '"logical_center_freq_hz", iq_message.get("center_freq")'

    for rel_path in demod_files:
        source = _read(rel_path)
        assert contract_snippet in source
