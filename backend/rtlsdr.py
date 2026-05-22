# Mock rtlsdr module for environments where the native librtlsdr C-library is not installed
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs

class RtlSdr:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("librtlsdr is not installed in this environment.")
