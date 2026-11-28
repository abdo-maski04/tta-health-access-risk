import pandas as pd
import pytest

from tta_risk.scoring.danger import compute_danger  # adapte l'import

pytestmark = pytest.mark.integration


def make_row(precip, tmax, **kw):
    base = dict(
        precip_mm=precip,
        tmax_c=tmax,
        rain_p65=5.0,
        rain_p80=10.0,
        rain_p90=20.0,
        heat_p65=28.0,
        heat_p80=32.0,
        heat_p90=36.0,
    )
    base.update(kw)
    return base


def danger_of(**kw):
    return compute_danger(pd.DataFrame([make_row(**kw)])).iloc[0]


def test_no_rain_below_one_mm():
    r = danger_of(precip=0.5, tmax=20)
    assert r.rain_level == 0 and r.danger == 0 and r.dominant == "none"


def test_rain_levels_at_boundaries():
    assert danger_of(precip=4.9, tmax=20).rain_level == 0
    assert danger_of(precip=5.0, tmax=20).rain_level == 1
    assert danger_of(precip=10.0, tmax=20).rain_level == 2
    assert danger_of(precip=20.0, tmax=20).rain_level == 3


def test_rain_only():
    r = danger_of(precip=12, tmax=20)
    assert r.rain_level == 2 and r.danger == 2 and r.dominant == "rain"


def test_heat_only():
    r = danger_of(precip=0, tmax=33)
    assert r.heat_level == 2 and r.danger == 2 and r.dominant == "heat"


def test_tie_gives_both():
    r = danger_of(precip=10.0, tmax=32)  # pluie 2, chaleur 2
    assert r.danger == 2 and r.dominant == "both"


def test_zero_zero_is_none_not_both():
    r = danger_of(precip=0, tmax=20)
    assert r.danger == 0 and r.dominant == "none"


def test_max_of_both():
    r = danger_of(precip=6, tmax=37)  # pluie 1, chaleur 3
    assert r.danger == 3 and r.dominant == "heat"


def test_missing_thresholds_gives_zero():
    r = danger_of(
        precip=50,
        tmax=40,
        rain_p65=None,
        rain_p80=None,
        rain_p90=None,
        heat_p65=None,
        heat_p80=None,
        heat_p90=None,
    )
    assert r.danger == 0 and r.dominant == "none"
