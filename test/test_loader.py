"""
Tests brewblox_ctl_lib.loader
"""

from brewblox_ctl_lib import loader


def test_cli_sources():
    assert loader.cli_sources()
