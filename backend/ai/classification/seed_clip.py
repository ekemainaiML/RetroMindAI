"""
Pre-compute CLIP text embeddings for all OEM vehicle models.

Runs on API startup in a background thread so the first request
is fast instead of waiting 20s for model loading + text embeddings.
"""

import logging
import threading

import numpy as np

logger = logging.getLogger(__name__)

_EMBEDDINGS_SEEDED = False
_seed_thread: threading.Thread | None = None


def seed_clip_embeddings(db_session=None):
    """
    Pre-compute and cache CLIP text embeddings for all active OEM models.
    Runs in a background thread — does not block API startup.
    Creates its own DB session so the caller's session can be closed.
    """
    global _EMBEDDINGS_SEEDED, _seed_thread
    if _EMBEDDINGS_SEEDED:
        return

    def _run():
        global _EMBEDDINGS_SEEDED
        try:
            from core.database import SessionLocal
            session = SessionLocal()
            try:
                from core.models import OEMManufacturer, OEMVehicleModel
                from sqlalchemy.orm import joinedload

                models = (
                    session.query(OEMVehicleModel)
                    .join(OEMManufacturer)
                    .options(joinedload(OEMVehicleModel.manufacturer))
                    .filter(OEMVehicleModel.is_active.is_(True))
                    .all()
                )

                if not models:
                    logger.info("No OEM models to seed CLIP embeddings for")
                    _EMBEDDINGS_SEEDED = True
                    return

                from ai.classification.clip_classifier import get_clip_classifier

                clip = get_clip_classifier()

                by_type: dict[str, list[dict]] = {}
                for m in models:
                    vt = m.vehicle_type or "unknown"
                    if vt not in by_type:
                        by_type[vt] = []
                    by_type[vt].append({
                        "id": str(m.id),
                        "manufacturer_name": m.manufacturer.name if m.manufacturer else "",
                        "model_name": m.model_name,
                        "vehicle_type": vt,
                    })

                dummy_img = np.zeros((224, 224, 3), dtype=np.uint8)
                for vt, oem_list in by_type.items():
                    clip._compute_text_embeddings(oem_list, vehicle_type=vt)
                    logger.info("Seeded CLIP embeddings for %s (%d models)", vt, len(oem_list))

                _EMBEDDINGS_SEEDED = True
                logger.info("CLIP text embeddings seeded for %d vehicle types", len(by_type))
            finally:
                session.close()
        except Exception as e:
            logger.warning("Failed to seed CLIP embeddings (non-fatal): %s", e)
            _EMBEDDINGS_SEEDED = True

    _seed_thread = threading.Thread(target=_run, daemon=True)
    _seed_thread.start()
    logger.info("CLIP embedding seeding started in background thread")
