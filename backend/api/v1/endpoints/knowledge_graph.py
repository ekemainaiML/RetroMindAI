import uuid
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_workshop
from core.database import get_db
from core.models import Intake, Job

router = APIRouter()


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    confidence: float
    risk_state: str
    compliance_state: str


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str
    weight: int


class KnowledgeGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


@router.get("/knowledge-graph", response_model=KnowledgeGraph)
async def get_knowledge_graph(
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    workshop_uuid = uuid.UUID(workshop_id)
    jobs = (
        db.query(Job)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(
            Job.status.in_(["completed", "partial_complete"]),
            Job.result.isnot(None),
            Intake.workshop_id == workshop_uuid,
        )
        .order_by(Job.created_at.desc())
        .all()
    )

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    job_data: list[tuple[Job, str, list[str], list[str]]] = []
    for job in jobs:
        result = job.result
        vc = result.get("vehicle_classification", {}) if result else {}
        vtype = vc.get("type", "unknown")
        risks = result.get("risks", []) if result else []

        deviation_keys: list[str] = []
        dev_result = result.get("deviation_result", {}) if result else {}
        for d in dev_result.get("deviations", []):
            param = d.get("parameter", "")
            sev = d.get("severity", "low")
            deviation_keys.append(f"{param}:{sev}")

        nodes.append(GraphNode(
            id=str(job.id),
            label=f"{vtype} ({str(job.intake_id)[:6]})",
            type=vtype,
            confidence=result.get("confidence_score", 0) if result else 0,
            risk_state=result.get("risk_summary", {}).get("system_risk_state", "normal") if result else "normal",
            compliance_state=result.get("compliance_state", "not_assessed") if result else "not_assessed",
        ))
        job_data.append((job, vtype, deviation_keys, [r.get("title", "") for r in risks]))

    for i in range(len(job_data)):
        for j in range(i + 1, len(job_data)):
            _, type_a, devs_a, risks_a = job_data[i]
            _, type_b, devs_b, risks_b = job_data[j]

            shared_devs = len(set(devs_a) & set(devs_b))
            shared_risks = len(set(risks_a) & set(risks_b))
            same_type = 2 if type_a == type_b and type_a != "unknown" else 0
            weight = shared_devs * 3 + shared_risks * 2 + same_type

            if weight > 0:
                edges.append(GraphEdge(
                    source=str(job_data[i][0].id),
                    target=str(job_data[j][0].id),
                    label=f"{shared_devs} shared deviation{'s' if shared_devs != 1 else ''}",
                    weight=min(weight, 10),
                ))

    return KnowledgeGraph(nodes=nodes, edges=edges)
