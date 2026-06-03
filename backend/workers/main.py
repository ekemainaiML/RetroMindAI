import logging
import os
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

logger = logging.getLogger(__name__)

_shutdown_requested = False


def _handle_signal(signum, frame):
    global _shutdown_requested
    if _shutdown_requested:
        logger.warning("Forced exit (second signal)")
        sys.exit(1)
    _shutdown_requested = True
    sig_name = signal.Signals(signum).name
    logger.info("Received %s, initiating graceful shutdown...", sig_name)


from workers.assessment import run_assessment  # noqa: F401, E402 - import so RQ discovers the function


def _requeue_stuck_jobs():
    try:
        from core.config import settings
        from core.database import SessionLocal
        from core.models import Job

        db = SessionLocal()
        try:
            from redis import Redis
            from rq import Queue

            redis_conn = Redis.from_url(settings.redis_url, socket_connect_timeout=3)
            queue = Queue("retromind-jobs", connection=redis_conn)
            active_rq_ids = set(queue.get_job_ids())

            stuck = (
                db.query(Job)
                .filter(Job.status.in_(["running", "queued"]))
                .all()
            )
            if not stuck:
                logger.info("No stuck jobs found on startup")
                return

            requeued = 0
            for job in stuck:
                if job.status == "running":
                    job.status = "queued"
                    job.current_stage = None
                    job.progress_pct = 0
                    job.error_message = "Worker restarted — job re-queued"
                    queue.enqueue(run_assessment, str(job.intake_id))
                    requeued += 1
                    logger.info("Re-queued stuck running job %s", job.id)
                elif job.status == "queued" and str(job.id) not in active_rq_ids:
                    job.error_message = "Job was orphaned — re-queued on worker start"
                    queue.enqueue(run_assessment, str(job.intake_id))
                    requeued += 1
                    logger.info("Re-queued orphaned queued job %s", job.id)

            db.commit()
            logger.info("Re-queued %d stuck job(s)", requeued)
        except Exception:
            logger.exception("Error during startup job recovery")
            db.rollback()
        finally:
            db.close()
    except Exception:
        logger.exception("Could not re-queue stuck jobs on startup")


def _run_worker():
    from rq import Connection, Worker
    from redis import Redis

    from core.config import settings

    conn = Redis.from_url(settings.redis_url)
    with Connection(conn):
        w = Worker(["retromind-jobs"])
        w.work()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    _requeue_stuck_jobs()

    from core.config import settings

    concurrency = settings.worker_concurrency
    logger.info("Starting worker with concurrency=%d", concurrency)

    if concurrency > 1:
        import multiprocessing
        processes = []
        for _ in range(concurrency):
            p = multiprocessing.Process(target=_run_worker, daemon=True)
            p.start()
            processes.append(p)
        for p in processes:
            p.join()
    else:
        _run_worker()
