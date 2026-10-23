import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest


@pytest.fixture(autouse=True)
def _offline_public_apis(monkeypatch):
    """Serve every public API wrapper from its mock payload unless a test
    opts into the live path explicitly."""
    monkeypatch.setenv("TOOLLLM_OFFLINE", "1")
