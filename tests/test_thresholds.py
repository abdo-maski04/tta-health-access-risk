import pytest

from tta_risk.db.database import get_connection

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def conn():
    try:
        c = get_connection()
    except Exception:
        pytest.skip("Base PostgreSQL non disponible")
    yield c
    c.close()


def fetch_one(conn, query):
    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchone()[0]


def test_146_communes_et_1752_lignes(conn):
    assert fetch_one(conn, "SELECT COUNT(DISTINCT commune_code) FROM weather.thresholds") == 146
    assert fetch_one(conn, "SELECT COUNT(*) FROM weather.thresholds") == 146 * 12


def test_pas_de_null_de_pluie_en_hiver(conn):
    # novembre à mars : il pleut assez, donc aucun seuil de pluie vide
    n = fetch_one(
        conn,
        """
        SELECT COUNT(*) FROM weather.thresholds
        WHERE month IN (11, 12, 1, 2, 3) AND rain_p90 IS NULL
    """,
    )
    assert n == 0


def test_les_null_de_pluie_sont_surtout_en_ete(conn):
    total = fetch_one(conn, "SELECT COUNT(*) FROM weather.thresholds WHERE rain_p90 IS NULL")
    ete = fetch_one(
        conn,
        """
        SELECT COUNT(*) FROM weather.thresholds
        WHERE month IN (6, 7, 8, 9) AND rain_p90 IS NULL
    """,
    )
    assert total > 0  # la règle des 20 jours s'applique bien
    assert ete == total  # et seulement entre juin et septembre


def test_la_chaleur_n_a_jamais_de_null(conn):
    n = fetch_one(
        conn,
        """
        SELECT COUNT(*) FROM weather.thresholds
        WHERE heat_p65 IS NULL OR heat_p80 IS NULL OR heat_p90 IS NULL
    """,
    )
    assert n == 0


def test_percentiles_dans_le_bon_ordre(conn):
    n = fetch_one(
        conn,
        """
        SELECT COUNT(*) FROM weather.thresholds
        WHERE rain_p65 > rain_p80 OR rain_p80 > rain_p90
           OR heat_p65 > heat_p80 OR heat_p80 > heat_p90
    """,
    )
    assert n == 0
