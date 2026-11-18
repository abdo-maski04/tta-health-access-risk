from src.tta_risk.db.database import get_connection, load_weather_rows


def test_upsert_query_history():
    rows1 = [("sidi abdo", "2023-01-01", 10.0, 20.0)]
    rows2 = [("sidi abdo", "2023-01-01", 15.0, 25.0)]
    load_weather_rows(rows1)
    load_weather_rows(rows2)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("select count(*) from weather.weather_daily where commune_code=%s and date=%s", ("sidi abdo", "2023-01-01"))
            result = cursor.fetchone()[0]
            assert result == 1, "le non chargements des lignes dupliquées des données météo a échoué"
