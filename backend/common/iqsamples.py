import numpy as np


def require_complex64(samples, source: str = "unknown") -> np.ndarray:
    """
    Enforce the in-memory IQ contract used across the pipeline.

    Contract:
    - numpy.ndarray
    - complex dtype
    - normalized/stored as complex64
    """
    if not isinstance(samples, np.ndarray):
        raise TypeError(
            f"{source}: expected numpy.ndarray IQ samples, got {type(samples).__name__}"
        )

    if samples.ndim != 1:
        samples = samples.reshape(-1)

    if not np.issubdtype(samples.dtype, np.complexfloating):
        raise TypeError(f"{source}: expected complex IQ dtype, got {samples.dtype}")

    samples = samples.astype(np.complex64, copy=False)
    if not samples.flags.c_contiguous:
        samples = np.ascontiguousarray(samples, dtype=np.complex64)
    return samples
