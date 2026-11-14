
import pytest

from src.tta_risk.db.database import get_connection

pytestmark = pytest.mark.integration

def test_connection_bdd():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            result=cursor.execute("select 1").fetchone()[0]
            assert result==1,"la connection avec bdd server est échoué"
