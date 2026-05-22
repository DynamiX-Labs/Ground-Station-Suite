import numpy as np
import pytest

from common.iqsamples import require_complex64


def test_require_complex64_accepts_complex_array():
    samples = np.array([1 + 2j, -0.25 + 0.5j], dtype=np.complex64)
    out = require_complex64(samples, source="test")
    assert out.dtype == np.complex64
    np.testing.assert_allclose(out, samples)


def test_require_complex64_casts_complex128_to_complex64():
    samples = np.array([1 + 2j, -0.25 + 0.5j], dtype=np.complex128)
    out = require_complex64(samples, source="test")
    assert out.dtype == np.complex64
    np.testing.assert_allclose(out, samples.astype(np.complex64))


def test_require_complex64_rejects_non_complex_input():
    samples = np.array([0, 255, 128, 127], dtype=np.uint8)
    with pytest.raises(TypeError):
        require_complex64(samples, source="test")
