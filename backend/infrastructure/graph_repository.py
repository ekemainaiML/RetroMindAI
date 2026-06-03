import logging
from datetime import datetime, timezone

from infrastructure.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class GraphRepository:
    def __init__(self, client: Neo4jClient):
        self.client = client

    def initialize_schema(self):
        queries = [
            "CREATE CONSTRAINT vehicle_id IF NOT EXISTS FOR (v:Vehicle) REQUIRE v.id IS UNIQUE",
            "CREATE INDEX deviation_type IF NOT EXISTS FOR (d:Deviation) ON (d.type)",
        ]
        for q in queries:
            self.client.run_query(q)

    def persist_assessment(self, assessment_result: dict, job_id: str, intake_id: str) -> bool:
        try:
            vehicle_type = (
                assessment_result.get("vehicle_classification", {}).get("type", "unknown")
            )
            confidence_score = assessment_result.get("confidence_score", 0)
            severity = assessment_result.get("deviation_summary", {}).get("severity", "low")
            deviation_result = assessment_result.get("deviation_result") or {}
            deviations = deviation_result.get("deviations", [])

            query = """
            MERGE (v:Vehicle {id: $intake_id})
            SET v.vehicle_type = $vehicle_type,
                v.confidence_score = $confidence_score,
                v.timestamp = $timestamp
            WITH v
            CREATE (a:Assessment {id: $job_id, confidence_score: $confidence_score, severity: $severity, timestamp: $timestamp})
            CREATE (v)-[:HAS_ASSESSMENT]->(a)
            WITH a
            UNWIND $deviations AS dev
            CREATE (d:Deviation {type: dev.parameter, severity: dev.severity, description: dev.notes, timestamp: $timestamp})
            CREATE (a)-[:HAS_DEVIATION]->(d)
            """
            self.client.run_query(query, {
                "intake_id": intake_id,
                "job_id": job_id,
                "vehicle_type": vehicle_type,
                "confidence_score": confidence_score,
                "severity": severity,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "deviations": deviations,
            })
            return True
        except Exception:
            logger.warning("Failed to persist assessment to Neo4j (non-fatal)", exc_info=True)
            return False

    def find_similar_retrofits(self, intake_id: str, max_results: int = 3) -> list[dict]:
        try:
            query = """
            MATCH (v:Vehicle {id: $intake_id})-[:HAS_ASSESSMENT]->(a)-[:HAS_DEVIATION]->(d)
            WITH v, COLLECT(DISTINCT d.type) AS my_devs
            MATCH (other:Vehicle)-[:HAS_ASSESSMENT]->(oa)-[:HAS_DEVIATION]->(od)
            WHERE other.id <> v.id
              AND od.type IN my_devs
            RETURN other.id AS vehicle_id,
                   other.vehicle_type AS type,
                   COUNT(od) AS matching_deviations,
                   oa.confidence_score AS confidence
            ORDER BY matching_deviations DESC
            LIMIT $max_results
            """
            results = self.client.run_query(query, {
                "intake_id": intake_id,
                "max_results": max_results,
            })
            return [
                {
                    "vehicle_id": r["vehicle_id"],
                    "type": r.get("type"),
                    "matching_deviations": r["matching_deviations"],
                    "confidence": round((r.get("confidence") or 0) / 100.0, 4),
                }
                for r in results
            ]
        except Exception:
            logger.warning("Failed to find similar retrofits (non-fatal)", exc_info=True)
            return []

    def get_retrofit_dna_summary(self, intake_id: str) -> dict:
        try:
            vehicle_count = self.client.run_query(
                "MATCH (v:Vehicle) RETURN COUNT(v) AS total"
            )
            assessment_count = self.client.run_query(
                "MATCH (a:Assessment) RETURN COUNT(a) AS total"
            )
            shared = self.client.run_query(
                """
                MATCH (v:Vehicle {id: $intake_id})-[:HAS_ASSESSMENT]->(a)-[:HAS_DEVIATION]->(d)
                WITH COLLECT(DISTINCT d.type) AS my_devs
                MATCH (other:Vehicle)-[:HAS_ASSESSMENT]->(oa)-[:HAS_DEVIATION]->(od)
                WHERE other.id <> $intake_id AND od.type IN my_devs
                RETURN COUNT(DISTINCT other) AS vehicles_with_shared_deviations
                """,
                {"intake_id": intake_id},
            )
            return {
                "total_vehicles": vehicle_count[0]["total"] if vehicle_count else 0,
                "total_assessments": assessment_count[0]["total"] if assessment_count else 0,
                "vehicles_with_shared_deviations": shared[0]["vehicles_with_shared_deviations"] if shared else 0,
            }
        except Exception:
            logger.warning("Failed to get DNA summary (non-fatal)", exc_info=True)
            return {}
