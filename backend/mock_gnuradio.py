# Mock gnuradio package for environments without native GNURadio installed
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs

import sys
from types import ModuleType

class MockModule(ModuleType):
    def __getattr__(self, name):
        mock_sub = MockModule(name)
        self.__dict__[name] = mock_sub
        return mock_sub

    def __call__(self, *args, **kwargs):
        return MockModule("mock_call_result")

# Create mock modules
gnuradio = MockModule("gnuradio")
gnuradio.__version__ = "3.10.mock"

gnuradio_blocks = MockModule("gnuradio.blocks")
gnuradio_gr = MockModule("gnuradio.gr")
gnuradio_lora = MockModule("gnuradio.lora_sdr")

# Register in sys.modules
sys.modules["gnuradio"] = gnuradio
sys.modules["gnuradio.blocks"] = gnuradio_blocks
sys.modules["gnuradio.gr"] = gnuradio_gr
sys.modules["gnuradio.lora_sdr"] = gnuradio_lora
