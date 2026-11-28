
import unittest
from datetime import timedelta

from airflow.dag_processing.dagbag import DagBag


class TestDailyRiskDag(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dagbag = DagBag(
            dag_folder="/opt/airflow/dags/daily_risk_dag.py",
        )

        cls.dag = cls.dagbag.dags["daily_health_access_risk"]

    def test_dag_import(self):
        self.assertEqual(self.dagbag.import_errors, {})
        self.assertIsNotNone(self.dag)

    def test_task_count(self):
        self.assertEqual(len(self.dag.tasks), 5)

    def test_task_ids(self):
        expected_tasks = {
            "check_prerequisites",
            "load_weather_forecast",
            "validate_forecast",
            "compute_daily_risk",
            "validate_risk_results",
        }

        self.assertEqual(
            set(self.dag.task_ids),
            expected_tasks,
        )

    def test_task_dependencies(self):
        expected_dependencies = {
            "check_prerequisites": set(),
            "load_weather_forecast": {"check_prerequisites"},
            "validate_forecast": {"load_weather_forecast"},
            "compute_daily_risk": {"validate_forecast"},
            "validate_risk_results": {"compute_daily_risk"},
        }

        for task_id, dependencies in expected_dependencies.items():
            task = self.dag.get_task(task_id)

            self.assertEqual(
                task.upstream_task_ids,
                dependencies,
            )

    def test_schedule(self):
        self.assertEqual(
        self.dag.timetable.expression,
        "0 6 * * *",
    )

    def test_timezone(self):
        self.assertEqual(
            self.dag.timezone.name,
            "Africa/Casablanca",
        )

    def test_catchup(self):
        self.assertFalse(self.dag.catchup)

    def test_max_active_runs(self):
        self.assertEqual(self.dag.max_active_runs, 1)

    def test_retries(self):
        expected_retries = {
            "check_prerequisites": 3,
            "load_weather_forecast": 3,
            "validate_forecast": 0,
            "compute_daily_risk": 3,
            "validate_risk_results": 0,
        }

        for task_id, retries in expected_retries.items():
            task = self.dag.get_task(task_id)

            self.assertEqual(task.retries, retries)

    def test_retry_delay(self):
        task = self.dag.get_task("load_weather_forecast")

        self.assertEqual(
            task.retry_delay,
            timedelta(minutes=5),
        )

    def test_execution_timeouts(self):
        for task in self.dag.tasks:
            expected_timeout = (
                30 if task.task_id == "load_weather_forecast"
                else 10
            )

            self.assertEqual(
                task.execution_timeout,
                timedelta(minutes=expected_timeout),
            )

    def test_trigger_rules(self):
        for task in self.dag.tasks:
            self.assertEqual(
                task.trigger_rule,
                "all_success",
            )


if __name__ == "__main__":
    unittest.main()
