"""Smoke-test the Streamlit app against the committed app data."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


def test_app_renders_without_errors():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert at.title[0].value.endswith("SponsorScope")
    assert len(at.dataframe) >= 1


def test_filters_do_not_crash():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.toggle[0].set_value(True)  # new grad only
    at.toggle[2].set_value(True)  # sponsor-friendly only
    at.radio[0].set_value("Remote only")
    at.slider[1].set_value(150)  # min salary $150K
    at.selectbox(key="posted_within").set_value("Last 7 days")
    at.run()
    assert not at.exception
    at.text_input[0].set_value("zzzz-no-such-job").run()
    assert not at.exception
