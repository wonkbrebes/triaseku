"""Gate keselamatan AI: build gagal bila kasus red flag tidak menjadi DARURAT."""
import json
from pathlib import Path

import pytest

from app import triage

DATA = json.loads((Path(__file__).parent / "scenarios.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("text", DATA["red_flag"])
def test_red_flag_selalu_darurat(text):
    flags = triage.find_red_flags(text)
    assert flags, f"Red flag tidak terdeteksi: {text}"
    assert triage.decide({}, flags)["arahan"] == triage.DARURAT


@pytest.mark.parametrize("text", DATA["no_red_flag"])
def test_keluhan_ringan_bukan_red_flag(text):
    assert triage.find_red_flags(text) == []


def test_ragu_memilih_lebih_aman():
    hasil = triage.decide({"keparahan": "entahlah", "durasi": "lama"}, [])
    assert hasil["arahan"] == triage.KONSULTASI


def test_keluhan_ringan_mandiri():
    hasil = triage.decide({"keparahan": "3", "durasi": "1 hari"}, [])
    assert hasil["arahan"] == triage.MANDIRI
