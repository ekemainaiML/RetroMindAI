import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from core.auth import get_current_workshop
from core.config import settings
from core.database import get_db
from core.models import Intake, Job

router = APIRouter()


def _build_pdf_context(job: Job, intake: Intake | None) -> dict:
    result = job.result or {}
    vc = result.get("vehicle_classification", {})

    recommendations = result.get("recommendations", [])
    _PRIORITY_MAP = {"high": "essential", "medium": "recommended", "low": "optional"}
    mapped_recs = []
    for r in recommendations:
        entry = dict(r)
        raw = entry.get("priority", "")
        entry["priority"] = _PRIORITY_MAP.get(raw, raw)
        mapped_recs.append(entry)

    total_cost = result.get("estimated_total_cost_inr", {})
    if isinstance(total_cost, (int, float)):
        cost_low = int(total_cost * 0.85)
        cost_mid = int(total_cost)
        cost_high = int(total_cost * 1.15)
    elif isinstance(total_cost, dict):
        cost_low = total_cost.get("low", total_cost.get("min", 0))
        cost_mid = total_cost.get("mid", total_cost.get("max", 0))
        cost_high = total_cost.get("high", total_cost.get("max", 0))
    else:
        cost_low = cost_mid = cost_high = 0

    view_slots = dict(intake.view_slots) if intake and intake.view_slots else {}
    submitted_views = [k for k, v in view_slots.items() if v is not None]
    risk_summary = result.get("risk_summary", {})

    return {
        "job_id": str(job.id),
        "intake_id": str(job.intake_id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "vehicle_type": vc.get("type", "unknown"),
        "confidence_score": result.get("confidence_score", 0),
        "compliance_state": result.get("compliance_state", "not_assessed"),
        "feasibility_score": result.get("feasibility_score", 0),
        "feasibility_label": result.get("feasibility_label", "unknown"),
        "assessment_state": result.get("assessment_state", "unknown"),
        "submitted_views": submitted_views,
        "quality_scores": dict(intake.quality_scores) if intake and intake.quality_scores else {},
        "total_recommendations": len(mapped_recs),
        "essential_count": sum(1 for r in mapped_recs if r.get("priority") == "essential"),
        "recommended_count": sum(1 for r in mapped_recs if r.get("priority") == "recommended"),
        "recommendations": [
            {
                "title": r.get("title"),
                "priority": r.get("priority"),
                "category": r.get("category"),
                "description": r.get("description"),
                "cost_estimate": r.get("cost_estimate"),
            }
            for r in mapped_recs
        ],
        "cost_low": cost_low,
        "cost_mid": cost_mid,
        "cost_high": cost_high,
        "estimated_days": result.get("estimated_days", 0),
        "critical_risks": risk_summary.get("critical_count", 0),
        "high_risks": risk_summary.get("high_count", 0),
        "medium_risks": risk_summary.get("medium_count", 0),
        "tooling_required": result.get("tooling_required", []),
        "skill_level_required": result.get("skill_level_required", "intermediate"),
        "deviations": result.get("deviation_result", {}).get("deviations", []),
        "digital_twin_available": result.get("digital_twin") is not None,
        "battery_placement": result.get("battery_placement"),
        "wiring_guidance": result.get("wiring_guidance"),
    }


@router.get("/reports/{job_id}/pdf")
async def export_report_pdf(
    job_id: uuid.UUID,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(Job.id == job_id, Intake.workshop_id == uuid.UUID(workshop_id))
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.result:
        raise HTTPException(status_code=400, detail="Job has no result")

    intake = db.query(Intake).filter(Intake.id == job.intake_id).first()
    context = _build_pdf_context(job, intake)

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=_render_report_html(context)).write_pdf()
        from fastapi.responses import Response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="assessment_report_{job.id}.pdf"'},
        )
    except ImportError:
        pass

    return HTMLResponse(
        content=_render_report_html(context),
        headers={"Content-Disposition": f'inline; filename="assessment_report_{job.id}.html"'},
    )


def _render_report_html(ctx: dict) -> str:
    recs = ctx.get("recommendations", [])
    rec_rows = "".join(
        f"""<tr>
          <td>{r.get('title', '')}</td>
          <td><span class="priority-{r.get('priority', 'optional')}">{r.get('priority', 'optional')}</span></td>
          <td>{r.get('category', '')}</td>
          <td>{r.get('description', '')}</td>
          <td>{r.get('cost_estimate', 'N/A')}</td>
        </tr>"""
        for r in recs
    )

    devs = ctx.get("deviations", [])
    dev_rows = "".join(
        f"<li>{d.get('parameter', '')}: {d.get('delta_pct', 0)}% deviation (severity: {d.get('severity', 'low')})</li>"
        for d in devs
    ) or "<li>No significant deviations detected</li>"

    views = ctx.get("submitted_views", [])
    view_items = "".join(f"<li>{v}</li>" for v in views) or "<li>No views submitted</li>"

    tools = ctx.get("tooling_required", [])
    tool_items = "".join(f"<li>{t}</li>" for t in tools) or "<li>No special tooling required</li>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @page {{ margin: 20mm; }}
  body {{ font-family: 'Helvetica', 'Arial', sans-serif; font-size: 11pt; line-height: 1.5; color: #333; }}
  h1 {{ font-size: 18pt; color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 4px; }}
  h2 {{ font-size: 14pt; color: #333; margin-top: 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; font-size: 10pt; }}
  th {{ background: #f5f5f5; }}
  .header {{ text-align: center; margin-bottom: 20px; }}
  .header h1 {{ border: none; font-size: 22pt; }}
  .meta {{ background: #f9f9f9; padding: 10px; border-radius: 4px; margin: 10px 0; }}
  .meta-item {{ display: inline-block; margin-right: 20px; }}
  .score {{ font-weight: bold; }}
  .priority-essential {{ color: #d93025; font-weight: bold; }}
  .priority-recommended {{ color: #f9ab00; font-weight: bold; }}
  .priority-optional {{ color: #1a73e8; }}
  ul {{ padding-left: 20px; }}
  .footer {{ text-align: center; font-size: 8pt; color: #999; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 10px; }}
</style></head><body>
<div class="header"><h1>Vehicle Assessment Report</h1></div>
<div class="meta">
  <div class="meta-item"><strong>Job ID:</strong> {ctx['job_id'][:8]}...</div>
  <div class="meta-item"><strong>Vehicle:</strong> {ctx['vehicle_type']}</div>
  <div class="meta-item"><strong>Status:</strong> {ctx['assessment_state']}</div>
  <div class="meta-item"><strong>Generated:</strong> {ctx['generated_at'][:10]}</div>
</div>

<h2>Classification & Confidence</h2>
<table>
  <tr><th>Vehicle Type</th><td>{ctx['vehicle_type']}</td></tr>
  <tr><th>Confidence Score</th><td class="score">{ctx['confidence_score']}%</td></tr>
  <tr><th>Compliance State</th><td>{ctx['compliance_state']}</td></tr>
  <tr><th>Feasibility</th><td>{ctx['feasibility_label']} ({ctx['feasibility_score']}%)</td></tr>
</table>

<h2>Evidence Submitted</h2>
<ul>{view_items}</ul>

<h2>Deviation Analysis</h2>
<ul>{dev_rows}</ul>

<h2>Recommendations ({ctx['total_recommendations']})</h2>
<table>
  <tr><th>Item</th><th>Priority</th><th>Category</th><th>Description</th><th>Cost Est.</th></tr>
  {rec_rows}
</table>

<h2>Cost Estimation</h2>
<table>
  <tr><th>Low Estimate</th><td>₹{ctx['cost_low']:,}</td></tr>
  <tr><th>Mid Estimate</th><td>₹{ctx['cost_mid']:,}</td></tr>
  <tr><th>High Estimate</th><td>₹{ctx['cost_high']:,}</td></tr>
  <tr><th>Estimated Days</th><td>{ctx['estimated_days']}</td></tr>
</table>

<h2>Risk Summary</h2>
<table>
  <tr><th>Critical</th><td style="color:#d93025;">{ctx['critical_risks']}</td></tr>
  <tr><th>High</th><td style="color:#f9ab00;">{ctx['high_risks']}</td></tr>
  <tr><th>Medium</th><td style="color:#1a73e8;">{ctx['medium_risks']}</td></tr>
</table>

<h2>Tooling & Skills Required</h2>
<p><strong>Skill Level:</strong> {ctx['skill_level_required']}</p>
<ul>{tool_items}</ul>

<div class="footer">Generated by RetroMind AI &mdash; Confidential</div>
</body></html>"""
