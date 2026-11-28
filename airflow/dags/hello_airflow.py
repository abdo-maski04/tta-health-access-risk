
import pendulum

from airflow.sdk import dag, task


@dag(
    dag_id="hello_airflow",
    start_date=pendulum.datetime(
        2026, 11, 28, tz="Africa/Casablanca"
    ),
    schedule=None,
    catchup=False,
    tags=["test"],
)
def hello_airflow():

    @task
    def extract():
        print("Extraction des données")
        return [10, 20, 30]

    @task
    def transform(data):
        print("Transformation des données")
        return [value * 2 for value in data]

    @task
    def load(data):
        print(f"Résultat final : {data}")

    load(transform(extract()))


hello_airflow()

