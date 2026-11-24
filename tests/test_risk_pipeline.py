import pandas as pd
import pytest

from tta_risk.db.database import (
    convert_risk_df_to_rows,
    get_connection,
    get_latest_forecast_date,
    load_risk_rows,
    read_forecast_with_thresholds,
)


@pytest.mark.unit
def test_convert_risk_rows_nan_becomes_none():
    df = pd.DataFrame([{
        "commune_code": "X",
        "forecast_issued_on": "2026-01-01",
        "target_date": "2026-01-02",
        "precip_mm": float("nan"),
        "tmax_c": 20.0,
        "rain_level": 0,
        "heat_level": 0,
        "danger": 0,
        "dominant": "none",
    }])

    row = convert_risk_df_to_rows(df)[0]

    assert row[3] is None


@pytest.mark.integration
def test_risk_upsert_is_idempotent():
    row = (
        "TEST_RISK",
        "2000-01-01",
        "2000-01-02",
        1.0,
        20.0,
        0,
        0,
        0,
        "none",
    )

    try:
        load_risk_rows([row])
        load_risk_rows([row])

        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM weather.risk_daily "
                "WHERE commune_code = 'TEST_RISK'"
            )
            assert cur.fetchone()[0] == 1

    finally:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM weather.risk_daily "
                "WHERE commune_code = 'TEST_RISK'"
            )
            conn.commit()


@pytest.mark.integration
def test_latest_forecast_joins_all_thresholds():
    issued = get_latest_forecast_date()
    df = read_forecast_with_thresholds(issued)

    assert df["commune_code"].nunique() == 146

    # La chaleur n'a jamais de NULL
    assert df["heat_p65"].notna().all()
