from __future__ import annotations

import src as cityscape


def test_version_is_defined() -> None:
    assert isinstance(cityscape.__version__, str)
    assert cityscape.__version__
