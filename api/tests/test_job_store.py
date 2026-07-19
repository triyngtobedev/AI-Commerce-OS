"""Testes do job store persistente em output/jobs.json."""

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from api.models.schemas import JobStatus
from api.services.job_store import JobStore


class TestJobStorePersistence(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store_path = Path(self.temp_dir.name) / "pipeline_jobs.db"
        self.store = JobStore(db_path=self.store_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_reload_job(self):
        job_id = uuid4()
        self.store.create_job(job_id, metadata={"topic": "Tunguska"})

        reloaded = JobStore(db_path=self.store_path)
        job = reloaded.get_job(job_id)

        self.assertIsNotNone(job)
        self.assertEqual(job["status"], JobStatus.QUEUED)
        self.assertEqual(job["metadata"]["topic"], "Tunguska")
        self.assertTrue(self.store_path.exists())

    def test_update_status_persists(self):
        job_id = uuid4()
        self.store.create_job(job_id)
        self.store.update_job_status(job_id, JobStatus.RUNNING)

        reloaded = JobStore(db_path=self.store_path)
        job = reloaded.get_job(job_id)

        self.assertEqual(job["status"], JobStatus.RUNNING)


if __name__ == "__main__":
    unittest.main()
