import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from core.auth import get_current_workshop
from core.database import get_db
from core.models import Intake, Job
from api.v1.endpoints.reports import build_report_sections

router = APIRouter()


def _render_value(val) -> str:
    if val is None:
        return "—"
    if isinstance(val, bool):
        return "Yes" if val else "No"
    if isinstance(val, float):
        return f"{val:.1f}"
    if isinstance(val, list):
        if not val:
            return "<span class=\"muted\">None</span>"
        items = "".join(f"<li>{_render_value(v)}</li>" for v in val)
        return f"<ul>{items}</ul>"
    if isinstance(val, dict):
        if not val:
            return "<span class=\"muted\">None</span>"
        rows = "".join(
            f"<tr><td class=\"key-col\">{k}</td><td>{_render_value(v)}</td></tr>"
            for k, v in val.items()
        )
        return f"<table class=\"inner\">{rows}</table>"
    return str(val)


def _render_section_html(section) -> str:
    c = section.content

    if section.id == "assessment_metadata":
        return f"""<h2>Assessment Metadata</h2>
<table>
  <tr><th>Job ID</th><td>{c.get('job_id', '-')}</td></tr>
  <tr><th>Intake ID</th><td>{c.get('intake_id', '-')}</td></tr>
  <tr><th>Workshop ID</th><td>{c.get('workshop_id', '-')}</td></tr>
  <tr><th>Status</th><td>{c.get('status', '-')}</td></tr>
  <tr><th>Created</th><td>{c.get('created_at', '-')[:19] if c.get('created_at') else '-'}</td></tr>
  <tr><th>Updated</th><td>{c.get('updated_at', '-')[:19] if c.get('updated_at') else '-'}</td></tr>
  <tr><th>Completed Stages</th><td>{_render_value(c.get('completed_stages', []))}</td></tr>
</table>"""

    if section.id == "vehicle_classification":
        alts = c.get("alternatives", [])
        alts_html = ""
        if alts:
            alts_html = "<p><strong>Alternatives:</strong></p><ul>" + "".join(
                f"<li>{a.get('type', '?')} ({a.get('confidence', 0):.0f}%)</li>" for a in alts
            ) + "</ul>"
        return f"""<h2>Vehicle Classification</h2>
<table>
  <tr><th>Type</th><td>{c.get('type', 'unknown')}</td></tr>
  <tr><th>Confidence</th><td>{c.get('confidence', 0)}%</td></tr>
  <tr><th>Human Confirmed</th><td>{"Yes" if c.get('human_confirmed') else "No"}</td></tr>
  <tr><th>Classifier</th><td>{c.get('classifier', 'N/A')}</td></tr>
  <tr><th>Model Loaded</th><td>{"Yes" if c.get('model_loaded') else "No"}</td></tr>
</table>
{alts_html}"""

    if section.id == "evidence_summary":
        views = c.get("views_submitted", [])
        missing = c.get("missing_views", [])
        low_q = c.get("low_quality_views", [])
        qs = c.get("quality_scores", {})
        qs_rows = "".join(
            f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in qs.items()
        )
        return f"""<h2>Evidence Summary</h2>
<table>
  <tr><th>All Required Views Submitted</th><td>{"Yes" if c.get('all_required_views_submitted') else "No"}</td></tr>
  <tr><th>Views Submitted</th><td>{_render_value(views)}</td></tr>
  <tr><th>Missing Views</th><td>{_render_value(missing)}</td></tr>
  <tr><th>Low Quality Views</th><td>{_render_value(low_q)}</td></tr>
  <tr><th>Swap Suspected</th><td>{"Yes" if c.get('swap_suspected') else "No"}</td></tr>
  <tr><th>Occluded Views</th><td>{_render_value(c.get('occluded_views', []))}</td></tr>
  <tr><th>Enhanced Views</th><td>{_render_value(c.get('enhanced_views', []))}</td></tr>
</table>
{('<h3>Quality Scores</h3><table class="inner">' + qs_rows + '</table>') if qs_rows else ''}"""

    if section.id == "deviation_summary":
        devs = c.get("deviations", [])
        top_issues = c.get("top_issues", [])
        dev_rows = ""
        if devs:
            dev_rows = """<h3>Individual Deviations</h3>
<table>
  <tr><th>Parameter</th><th>Estimated</th><th>Reference</th><th>Delta %</th><th>Severity</th></tr>""" + "".join(
                f"<tr><td>{d.get('parameter', '')}</td><td>{d.get('estimated', '')}</td><td>{d.get('reference', '')}</td><td>{d.get('delta_pct', 0)}%</td><td>{d.get('severity', 'low')}</td></tr>"
                for d in devs
            ) + "</table>"
        issues_html = ""
        if top_issues:
            issues_html = "<h3>Top Issues</h3><ul>" + "".join(f"<li>{t}</li>" for t in top_issues) + "</ul>"
        return f"""<h2>Deviation Summary</h2>
<table>
  <tr><th>Anomalies Detected</th><td>{c.get('anomalies_detected', 0)}</td></tr>
  <tr><th>Severity</th><td>{c.get('severity', 'low')}</td></tr>
  <tr><th>Deviation Score</th><td>{c.get('deviation_score', 100)}%</td></tr>
  <tr><th>Deviation Certainty</th><td>{c.get('deviation_certainty', 0)}%</td></tr>
  <tr><th>Critical Delamination</th><td>{"Yes" if c.get('critical_delamination') else "No"}</td></tr>
  <tr><th>Salvage Potential</th><td>{c.get('salvage_potential', 100)}%</td></tr>
</table>
{issues_html}
{dev_rows}"""

    if section.id == "confidence_and_risk":
        rc = c.get("risk_counts", {})
        reg = c.get("risk_register", [])
        reg_rows = ""
        if reg:
            reg_rows = "<h3>Risk Register</h3><table><tr><th>Risk</th><th>Severity</th><th>Mitigation</th></tr>" + "".join(
                f"<tr><td>{r.get('description', r.get('title', ''))}</td><td>{r.get('severity', '')}</td><td>{r.get('mitigation', 'N/A')}</td></tr>"
                for r in reg
            ) + "</table>"
        return f"""<h2>Confidence & Risk Summary</h2>
<table>
  <tr><th>Assessment State</th><td>{c.get('assessment_state', 'unknown')}</td></tr>
  <tr><th>Confidence Score</th><td>{c.get('confidence_score', 0)}%</td></tr>
  <tr><th>System Risk State</th><td>{c.get('system_risk_state', 'normal')}</td></tr>
  <tr><th>Critical Risks</th><td>{rc.get('critical', 0)}</td></tr>
  <tr><th>High Risks</th><td>{rc.get('high', 0)}</td></tr>
  <tr><th>Medium Risks</th><td>{rc.get('medium', 0)}</td></tr>
  <tr><th>Low Risks</th><td>{rc.get('low', 0)}</td></tr>
</table>
{reg_rows}"""

    if section.id == "compliance_state":
        return f"""<h2>Compliance State</h2>
<table>
  <tr><th>Compliance State</th><td>{c.get('compliance_state', 'not_assessed')}</td></tr>
  <tr><th>Needs Confirmation</th><td>{"Yes" if c.get('needs_confirmation') else "No"}</td></tr>
  <tr><th>Feasibility Score</th><td>{c.get('feasibility_score', 0)}%</td></tr>
  <tr><th>Feasibility Label</th><td>{c.get('feasibility_label', 'unknown')}</td></tr>
</table>"""

    if section.id == "recommendations_overview":
        recs = c.get("recommendations", [])
        rec_rows = "".join(
            f"""<tr>
          <td>{r.get('title', '')}</td>
          <td><span class="priority-{r.get('priority', 'optional')}">{r.get('priority', 'optional')}</span></td>
          <td>{r.get('category', '')}</td>
          <td>{r.get('description', '')}</td>
          <td>{"<strong>BLOCKING</strong>" if r.get('blocking') else ""}</td>
        </tr>"""
            for r in recs
        )
        return f"""<h2>Recommendations ({c.get('total_recommendations', 0)})</h2>
<p>Essential: {c.get('essential_count', 0)} | Recommended: {c.get('recommended_count', 0)}</p>
<table>
  <tr><th>Item</th><th>Priority</th><th>Category</th><th>Description</th><th>Blocking</th></tr>
  {rec_rows}
</table>"""

    if section.id == "battery_placement":
        recs = c.get("battery_recommendations", [])
        zones = (c.get("battery_zones") or {}).get("zones", []) if c.get("battery_zones") else []
        rec_html = ""
        if recs:
            rec_html = "<h3>Recommendations</h3>" + "".join(
                f"<div class=\"rec-card\"><strong>{r.get('title', '')}</strong><p>{r.get('description', '')}</p></div>"
                for r in recs
            )
        zones_html = ""
        if zones:
            recommended = (c.get("battery_zones") or {}).get("recommended_zone", "")
            zones_html = "<h3>Computed Zones</h3>" + "".join(
                f"<div class=\"rec-card{' recommended' if z.get('id') == recommended else ''}\"><strong>{z.get('label', '')}</strong>{' ★ Best' if z.get('id') == recommended else ''}<p>{_render_value(z.get('max_dimensions_mm', {}))}</p></div>"
                for z in zones[:6]
            )
        return f"""<h2>Battery Placement</h2>
<p class="muted">Optimized battery placement zones and recommendations based on vehicle geometry and detected deviations.</p>
{zones_html}
{rec_html}
{('<p class="muted">No battery placement recommendations available.</p>' if not recs and not zones else '')}"""

    if section.id == "wiring_guidance":
        recs = c.get("wiring_recommendations", [])
        if not recs:
            return """<h2>Wiring Guidance</h2>
<p class="muted">No wiring recommendations available.</p>"""
        rec_html = "".join(
            f"<div class=\"rec-card\"><strong>{r.get('title', '')}</strong><p>{r.get('description', '')}</p></div>"
            for r in recs
        )
        return f"""<h2>Wiring Guidance</h2>
<p class="muted">Wiring routing guidance accounting for deviation-triggered caution zones and spatial constraints.</p>
{rec_html}"""

    if section.id == "cost_estimation":
        cost = c.get("estimated_total_cost_inr", {})
        breakdown = c.get("recommendation_breakdown", [])
        bd_rows = ""
        if breakdown:
            bd_rows = "<h3>Recommendation Breakdown</h3><table><tr><th>Item</th><th>Cost Estimate</th></tr>" + "".join(
                f"<tr><td>{b.get('title', '')}</td><td>{_render_value(b.get('cost_estimate'))}</td></tr>"
                for b in breakdown
            ) + "</table>"
        cost_low = cost.get('low', 0) if not isinstance(cost.get('low'), dict) else 0
        cost_mid = cost.get('mid', 0) if not isinstance(cost.get('mid'), dict) else 0
        cost_high = cost.get('high', 0) if not isinstance(cost.get('high'), dict) else 0
        return f"""<h2>Cost Estimation</h2>
<table>
  <tr><th>Low Estimate</th><td>₹{cost_low:,}</td></tr>
  <tr><th>Mid Estimate</th><td>₹{cost_mid:,}</td></tr>
  <tr><th>High Estimate</th><td>₹{cost_high:,}</td></tr>
  <tr><th>Estimated Days</th><td>{c.get('estimated_days', 0)}</td></tr>
</table>
{bd_rows}"""

    if section.id == "tooling_and_skills":
        tools = c.get("tooling_required", [])
        tool_items = "".join(f"<li>{t}</li>" for t in tools) or "<li>No special tooling required</li>"
        return f"""<h2>Tooling & Skill Requirements</h2>
<table>
  <tr><th>Skill Level Required</th><td>{c.get('skill_level_required', 'intermediate')}</td></tr>
</table>
<h3>Tooling Required</h3>
<ul>{tool_items}</ul>"""

    if section.id == "digital_twin":
        dims = c.get("dimensions")
        devs_3d = c.get("deviations_3d", [])
        comps = c.get("retrofit_components", [])
        dims_rows = ""
        if dims:
            dims_rows = "<h3>Dimensions</h3>" + _render_value(dims)
        devs_rows = ""
        if devs_3d:
            devs_rows = "<h3>3D Deviations</h3>" + _render_value(devs_3d)
        comps_html = ""
        if comps:
            comps_html = "<h3>Retrofit Components</h3>" + _render_value(comps)
        avail = c.get("twin_available", False)
        return f"""<h2>Digital Twin Data</h2>
<p><strong>Twin Available:</strong> {"Yes" if avail else "No"}</p>
{dims_rows}
{devs_rows}
{comps_html}"""

    if section.id == "infrastructure_degradation":
        svc = c.get("service_status", {})
        degs = c.get("degradations", [])
        all_ok = c.get("all_operational", True)
        svc_rows = "".join(
            f"<tr><td>{name}</td><td>{'✅' if status == 'connected' else '⚠️'} {status}</td></tr>"
            for name, status in svc.items()
        )
        deg_html = ""
        if degs:
            deg_html = "<h3>Active Degradations</h3>" + "".join(
                f"<div class=\"warn-card\"><strong>{d.get('service', '')}</strong><p>{d.get('message', '')}</p></div>"
                for d in degs
            )
        return f"""<h2>Infrastructure Degradation</h2>
<h3>Service Status</h3>
<table>
  <tr><th>Service</th><th>Status</th></tr>
  {svc_rows}
</table>
{('' if all_ok else '<p class="muted">All services operational.</p>')}
{deg_html}"""

    if section.id == "retrofit_dna":
        matches = c.get("matches", [])
        match_items = ""
        if matches:
            match_items = "".join(
                f"<div class=\"rec-card\"><strong>{m.get('vehicle_id', '')}</strong> — {m.get('type', '')} ({(m.get('confidence', 0) * 100 if isinstance(m.get('confidence'), (int, float)) else 0):.0f}%)</div>"
                for m in matches
            )
        else:
            match_items = '<p class="muted">No similar retrofit patterns found.</p>'
        return f"""<h2>Retrofit DNA Matches</h2>
<p><strong>Current Vehicle:</strong> {c.get('current_vehicle_type', 'unknown')}</p>
<p><strong>Similar Matches Found:</strong> {c.get('matches_found', 0)}</p>
{match_items}"""

    # fallback: render all key-value pairs
    skip_keys = {
        "deviations", "top_issues", "recommendations",
        "estimated_total_cost_inr", "degradations", "matches",
        "current_vehicle_type", "current_vehicle_label", "current_intake_id", "matches_found",
        "battery_recommendations", "wiring_recommendations",
    }
    rows = "".join(
        f"<tr><th>{k.replace('_', ' ').title()}</th><td>{_render_value(v)}</td></tr>"
        for k, v in c.items()
        if k not in skip_keys and v is not None
    )
    return f"""<h2>{section.title}</h2>
<table>
  {rows if rows else '<tr><td class="muted">No data available</td></tr>'}
</table>"""


def _render_report_html(sections, branding: dict | None = None) -> str:
    body = "".join(_render_section_html(s) for s in sections)
    b = branding or {}
    primary = b.get("primary_color") or "#1a73e8"
    secondary = b.get("secondary_color") or "#7c3aed"
    logo = b.get("logo_url") or ""
    logo_html = f'<img src="{logo}" style="max-height:40px;margin-bottom:10px;" />' if logo else ""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @page {{ margin: 18mm 15mm; }}
  body {{ font-family: 'Helvetica', 'Arial', sans-serif; font-size: 10pt; line-height: 1.5; color: #222; }}
  h1 {{ font-size: 20pt; color: {primary}; border-bottom: 2px solid {primary}; padding-bottom: 5px; margin-top: 0; }}
  h2 {{ font-size: 13pt; color: {primary}; margin-top: 22px; margin-bottom: 8px; border-bottom: 1px solid #e0e0e0; padding-bottom: 3px; }}
  h3 {{ font-size: 11pt; color: #333; margin-top: 14px; margin-bottom: 6px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 5px 7px; text-align: left; font-size: 9pt; }}
  th {{ background: #f0f4f8; font-weight: 600; }}
  .key-col {{ font-weight: 600; color: #555; width: 30%; }}
  .inner {{ margin: 4px 0; }}
  .inner th {{ background: #f8f9fa; }}
  .muted {{ color: #888; }}
  .header {{ text-align: center; margin-bottom: 22px; }}
  .header h1 {{ border: none; font-size: 24pt; }}
  .meta {{ background: #f7f9fc; padding: 10px 14px; border-radius: 4px; margin: 10px 0; font-size: 9pt; }}
  .meta-item {{ display: inline-block; margin-right: 22px; }}
  .priority-essential {{ color: #d93025; font-weight: bold; }}
  .priority-recommended {{ color: #e37400; font-weight: bold; }}
  .priority-optional {{ color: {primary}; }}
  ul {{ padding-left: 18px; margin: 4px 0; }}
  li {{ margin-bottom: 2px; }}
  .rec-card {{ border: 1px solid #e0e0e0; border-radius: 4px; padding: 8px 10px; margin-bottom: 6px; background: #fafafa; font-size: 9pt; }}
  .rec-card.recommended {{ border-color: #34a853; background: #f0faf4; }}
  .warn-card {{ border: 1px solid #f9ab00; border-radius: 4px; padding: 8px 10px; margin-bottom: 6px; background: #fff8e1; font-size: 9pt; }}
  .rec-card strong {{ font-size: 10pt; }}
  .footer {{ text-align: center; font-size: 7.5pt; color: #aaa; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 8px; }}
</style></head><body>
<div class="header">{logo_html}<h1>Vehicle Assessment Report</h1></div>
<div class="meta">
  <span class="meta-item"><strong>Generated:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</span>
  <span class="meta-item"><strong>Sections:</strong> {len(sections)}</span>
</div>
{body}
<div class="footer">Generated by RetroMind AI &mdash; Confidential</div>
</body></html>"""


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
    sections = build_report_sections(job, intake, job.result)
    from core.models import Workshop as WorkshopModel
    w = db.query(WorkshopModel).filter(WorkshopModel.id == uuid.UUID(workshop_id)).first()
    branding = w.branding if w else {}
    html = _render_report_html(sections, branding)

    try:
        from weasyprint import HTML  # type: ignore[import-untyped]
        pdf_bytes = HTML(string=html).write_pdf()
        from fastapi.responses import Response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="assessment_report_{job.id}.pdf"'},
        )
    except (ImportError, OSError):
        pass

    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'inline; filename="assessment_report_{job.id}.html"'},
    )
