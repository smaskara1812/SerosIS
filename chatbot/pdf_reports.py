"""
PDF report generation.

Templates are JSON files in chatbot/pdf_templates/.
To customise a template:
  1. Open the ReportBro designer at http://localhost:9191/designer.html
  2. In the browser console: rb.load(await fetch('/api/pdf-templates/hazard_cards/').then(r=>r.json()))
  3. Edit visually, click PREVIEW to test
  4. In the browser console: copy(JSON.stringify(rb.getReport()))
  5. Paste into chatbot/pdf_templates/hazard_cards.json (or rig-specific file)

Rig-specific templates: hazard_cards.EE02.json overrides hazard_cards.json for rig EE02.
"""

import json
from pathlib import Path
from reportbro import Report, ReportBroError

_TEMPLATES_DIR = Path(__file__).parent / "pdf_templates"


def load_template(report_name: str, rig: str | None = None) -> dict:
    """
    Load a template JSON.  Checks rig-specific file first, then default.

    hazard_cards + EE02  →  tries hazard_cards.EE02.json, falls back to hazard_cards.json
    """
    candidates = []
    if rig:
        safe_rig = rig.replace(" ", "_").replace("/", "_")
        candidates.append(_TEMPLATES_DIR / f"{report_name}.{safe_rig}.json")
    candidates.append(_TEMPLATES_DIR / f"{report_name}.json")

    for path in candidates:
        if path.exists():
            return json.loads(path.read_text())

    raise FileNotFoundError(
        f"No template found for '{report_name}'"
        + (f" (rig: {rig})" if rig else "")
        + f". Expected one of: {[str(p) for p in candidates]}"
    )


def save_template(report_name: str, template: dict, rig: str | None = None) -> Path:
    """Persist a designer-exported template JSON to disk."""
    if rig:
        safe_rig = rig.replace(" ", "_").replace("/", "_")
        path = _TEMPLATES_DIR / f"{report_name}.{safe_rig}.json"
    else:
        path = _TEMPLATES_DIR / f"{report_name}.json"
    path.write_text(json.dumps(template, indent=2))
    return path


def render_pdf(report_name: str, data: dict, rig: str | None = None) -> bytes:
    """Load template and render PDF. Raises FileNotFoundError or ReportBroError."""
    template = load_template(report_name, rig=rig)
    report = Report(template, data)
    if report.errors:
        raise ReportBroError(report.errors)
    return bytes(report.generate_pdf())


# ── Per-report data builders ──────────────────────────────────────────────────

def generate_hazard_cards_pdf(rows: list, rig_label="All Rigs", period_label="All Time",
                               rig: str | None = None) -> bytes:
    data = {
        "report_title": "Hazard ID Cards Report",
        "rig_label": rig_label,
        "period_label": period_label,
        "total_count": len(rows),
        "hazard_cards": [
            {
                "date":        str(r.get("date", "") or ""),
                "rig":         r.get("rig", "") or "",
                "hazard_type": r.get("hazard_type", "") or "",
                "reported_by": r.get("reported_by", "") or "",
                "status":      "Open" if r.get("status") != "C" else "Closed",
                "summary":     (r.get("summary", "") or "")[:120],
            }
            for r in rows
        ],
    }
    return render_pdf("hazard_cards", data, rig=rig)
