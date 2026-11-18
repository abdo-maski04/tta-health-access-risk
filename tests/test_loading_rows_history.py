import pytest

from tta_risk.db.database import get_connection, load_weather_rows


pytestmark = pytest.mark.integration


def test_load_weather_rows():
    rows = [("sidi abdo", "2023-01-01", 10.0, 20.0)]

    try:
        load_weather_rows(rows)
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM weather.weather_daily
                    WHERE commune_code = %s AND date = %s
                    """,
                    ("sidi abdo", "2023-01-01"),
                )
                result = cursor.fetchone()[0]
        assert result == 1, "Le chargement des données météo a échoué"
    finally:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM weather.weather_daily
                    WHERE commune_code = %s AND date = %s
                    """,
                    ("sidi abdo", "2023-01-01"),
                )
