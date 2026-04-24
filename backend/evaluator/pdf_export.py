"""
PDF export using xhtml2pdf.
Generates a styled IELTS evaluation report using HTML/CSS.
Works natively across platforms without requiring C-bindings/DLLs.
"""

import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _band_color(score: float) -> str:
    """Returns a color hex based on IELTS band score."""
    if score >= 7.5:
        return "#16a34a"  # green
    elif score >= 6.0:
        return "#2563eb"  # blue
    elif score >= 5.0:
        return "#d97706"  # amber
    else:
        return "#dc2626"  # red


def generate_evaluation_pdf(evaluation) -> bytes:
    """
    Generates a PDF evaluation report for the given Evaluation model instance.
    Returns raw PDF bytes.
    """
    try:
        from xhtml2pdf import pisa
    except ImportError:
        raise RuntimeError("xhtml2pdf is not installed. Run: pip install xhtml2pdf")

    scores = evaluation.scores or {}
    feedback = evaluation.feedback or {}
    overall = scores.get("overall", "N/A")
    overall_color = _band_color(float(overall)) if isinstance(overall, (int, float)) else "#374151"

    criteria_rows = ""
    for key, label in [
        ("task_response", "Task Achievement" if evaluation.task_type == "task1" else "Task Response"),
        ("coherence", "Coherence & Cohesion"),
        ("lexical", "Lexical Resource"),
        ("grammar", "Grammatical Range & Accuracy"),
    ]:
        score = scores.get(key, "N/A")
        fb = feedback.get(key, "No feedback available.")
        score_float = float(score) if isinstance(score, (int, float)) else 5.0
        
        # We use a simple 100% width table to simulate a layout
        criteria_rows += f"""
        <div class="criterion-card">
            <table width="100%">
                <tr>
                    <td align="left"><span class="criterion-label">{label}</span></td>
                    <td align="right"><span class="criterion-score" style="color: {_band_color(score_float)};">{score}</span></td>
                </tr>
            </table>
            <div style="background-color: #e5e7eb; height: 6px; margin-top: 5px; margin-bottom: 10px;">
                <div style="background-color: {_band_color(score_float)}; height: 6px; width: {int(((score_float - 1) / 8) * 100)}%;"></div>
            </div>
            <p class="criterion-feedback">{fb}</p>
        </div>"""

    improvements = feedback.get("improvements", [])
    improvements_html = "".join(f"<li>{imp}</li>" for imp in improvements)

    essay_preview = evaluation.essay_text[:1000] + (
        "..." if len(evaluation.essay_text) > 1000 else ""
    )

    date_str = evaluation.created_at.strftime("%B %d, %Y") if evaluation.created_at else ""
    task_label = "Writing Task 1 (Academic)" if evaluation.task_type == "task1" else "Writing Task 2"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>T1T2.ai IELTS Evaluation Report</title>
<style>
  body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 11pt;
    color: #111827;
    line-height: 1.5;
  }}
  .header {{
    border-bottom: 2px solid #6366f1;
    padding-bottom: 15px;
    margin-bottom: 25px;
  }}
  .brand {{ font-size: 24pt; font-weight: bold; color: #6366f1; }}
  .tagline {{ color: #6b7280; font-size: 11pt; }}
  .meta-text {{ color: #6b7280; font-size: 10pt; text-align: right; }}

  .overall-section {{
    background-color: #f9fafb;
    border: 1px solid #e5e7eb;
    padding: 20px;
    margin-bottom: 25px;
  }}
  .overall-score {{
    font-size: 36pt;
    font-weight: bold;
    color: {overall_color};
  }}
  .overall-title {{ font-size: 16pt; font-weight: bold; margin-bottom: 5px; }}
  
  .section-title {{
    font-size: 14pt;
    font-weight: bold;
    color: #374151;
    margin-bottom: 15px;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 5px;
  }}

  .criterion-card {{
    background-color: #f9fafb;
    border: 1px solid #e5e7eb;
    padding: 15px;
    margin-bottom: 15px;
  }}
  .criterion-label {{ font-weight: bold; font-size: 11pt; color: #374151; }}
  .criterion-score {{ font-size: 14pt; font-weight: bold; }}
  .criterion-feedback {{ color: #4b5563; font-size: 10pt; }}

  .improvements-section {{ margin-top: 20px; }}
  .improvements-section ul {{ padding-left: 20px; }}
  .improvements-section li {{
    margin-bottom: 8px;
    font-size: 10pt;
    color: #374151;
  }}

  .essay-section {{
    margin-top: 25px;
    background-color: #f9fafb;
    border: 1px solid #e5e7eb;
    padding: 15px;
  }}
  .essay-text {{
    color: #4b5563;
    font-size: 10pt;
    white-space: pre-wrap;
  }}

  .footer {{
    margin-top: 40px;
    border-top: 1px solid #e5e7eb;
    padding-top: 10px;
    text-align: center;
    color: #9ca3af;
    font-size: 9pt;
  }}
</style>
</head>
<body>

<div class="header">
    <table width="100%">
        <tr>
            <td align="left" width="60%">
                <div class="brand">T1T2.ai</div>
                <div class="tagline">Your AI Examiner for IELTS Writing Tasks</div>
            </td>
            <td align="right" width="40%" class="meta-text">
                <strong>{task_label}</strong><br/>
                {date_str}<br/>
                Evaluation #{evaluation.id}<br/>
                {evaluation.model_used or 'AI Evaluated'}
            </td>
        </tr>
    </table>
</div>

<div class="overall-section">
    <table width="100%">
        <tr>
            <td width="20%" align="center" valign="middle">
                <div class="overall-score">{overall}</div>
                <div style="font-size: 10pt; color: #6b7280;">Overall</div>
            </td>
            <td width="80%" align="left" valign="middle" style="padding-left: 20px;">
                <div class="overall-title">IELTS Band Score: {overall}</div>
                <div style="color: #6b7280; font-size: 10pt;">
                    {evaluation.word_count} words &bull; {'Cache hit' if evaluation.cache_hit else 'Fresh evaluation'}
                </div>
            </td>
        </tr>
    </table>
</div>

<div class="section-title">Criterion Scores &amp; Feedback</div>
{criteria_rows}

<div class="improvements-section">
  <div class="section-title">Key Improvement Areas</div>
  <ul>{improvements_html}</ul>
</div>

<div class="essay-section">
  <div class="section-title">Essay (excerpt)</div>
  <p class="essay-text">{essay_preview}</p>
</div>

<div class="footer">
  Generated by T1T2.ai &bull; t1t2.ai &bull; This evaluation is AI-generated and for preparation purposes only.<br/>
  Results may vary from official IELTS examiner marking.
</div>

</body>
</html>"""

    result_io = io.BytesIO()
    # xhtml2pdf expects bytes for source or a unicode string
    pdf = pisa.CreatePDF(io.StringIO(html_content), dest=result_io)
    
    if pdf.err:
        raise RuntimeError("PDF generation failed via xhtml2pdf.")
        
    return result_io.getvalue()
