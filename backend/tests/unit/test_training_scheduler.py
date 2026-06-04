from unittest.mock import MagicMock, patch


from core.models import Job
from workers.training_scheduler import (
    _get_heuristic_baseline,
    scheduled_retrain,
)


class TestTrainingScheduler:
    def test_baseline_constant(self):
        assert _get_heuristic_baseline() == 0.75

    def test_scheduled_retrain_no_unprocessed(self, monkeypatch):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        monkeypatch.setattr("workers.training_scheduler.SessionLocal", lambda: mock_db)

        with patch("workers.training_scheduler.logger") as mock_log:
            scheduled_retrain()
            mock_log.info.assert_any_call(
                "Not enough new samples for retraining (%d < %d)", 0, 10
            )

    def test_scheduled_retrain_import_error(self, monkeypatch):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 50
        monkeypatch.setattr("workers.training_scheduler.SessionLocal", lambda: mock_db)

        def _raise_import():
            raise ImportError("No module named torch")

        monkeypatch.setitem(__builtins__, "__import__", lambda *a, **kw: _raise_import())

        with patch.object(Job, "trained_on", None, create=True):
            scheduled_retrain()

    def test_insufficient_samples_skips_training(self, monkeypatch):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 3
        monkeypatch.setattr("workers.training_scheduler.SessionLocal", lambda: mock_db)

        with patch(
            "workers.training_scheduler.logger"
        ) as mock_log:
            scheduled_retrain()
            mock_log.info.assert_any_call(
                "Not enough new samples for retraining (%d < %d)", 3, 10
            )

    def test_trained_on_column_on_model(self):
        job = Job()
        assert hasattr(job, "trained_on")
        assert job.trained_on is None
