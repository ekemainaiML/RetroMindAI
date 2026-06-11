import logging
import os
from threading import Lock

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(self):
        self._driver = None
        self._lock = Lock()

    def connect(self):
        if self._driver is not None:
            return True
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        with self._lock:
            if self._driver is not None:
                return True
            try:
                self._driver = GraphDatabase.driver(uri, auth=(user, password))
                self._driver.verify_connectivity()
                logger.info("Connected to Neo4j at %s", uri)
                return True
            except Exception:
                logger.warning("Neo4j connection failed (non-fatal)")
                self._driver = None
                return False

    def close(self):
        with self._lock:
            if self._driver is not None:
                try:
                    self._driver.close()
                except Exception:
                    pass
                self._driver = None

    def verify_connectivity(self) -> bool:
        if self._driver is None:
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def run_query(self, query: str, params: dict = None) -> list[dict]:  # type: ignore[assignment]
        if self._driver is None and not self.connect():
            return []
        try:
            with self._driver.session() as session:
                result = session.run(query, parameters=params or {})
                return [dict(r) for r in result]
        except Exception:
            logger.warning("Neo4j query failed (non-fatal)", exc_info=True)
            return []
