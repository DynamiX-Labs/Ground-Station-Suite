# Mock SoapySDR module for environments where the native C++ library is not installed
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs

SOAPY_SDR_RX = 0
SOAPY_SDR_TX = 1

SOAPY_SDR_CS8 = "CS8"
SOAPY_SDR_CS16 = "CS16"
SOAPY_SDR_CF32 = "CF32"
SOAPY_SDR_CF64 = "CF64"

class Device:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("SoapySDR is not installed in this environment.")

    @staticmethod
    def enumerate(*args, **kwargs):
        return []
