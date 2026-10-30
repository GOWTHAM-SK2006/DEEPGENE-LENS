"""Professional ReportLab PDF reports for DeepGeneLens analyses."""

from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase.pdfmetrics import stringWidth

ORANGE = colors.HexColor("#ED713D")
NAVY = colors.HexColor("#19243A")
MUTED = colors.HexColor("#667085")
LIGHT = colors.HexColor("#F4F6F8")
BORDER = colors.HexColor("#DDE3EA")
GREEN = colors.HexColor("#25885B")
PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 48


class CompositionChart(Flowable):
    """Draw a compact nucleotide composition bar and donut chart."""

    def __init__(self, composition: dict[str, float], gc_content: float) -> None:
        super().__init__()
        self.composition = composition
        self.gc_content = gc_content
        self.width = PAGE_WIDTH - (2 * MARGIN)
        self.height = 150

    def draw(self) -> None:
        canvas = self.canv
        x, y = 0, 0
        canvas.setFillColor(LIGHT)
        canvas.roundRect(x, y, self.width, self.height, 8, fill=1, stroke=0)

        center_x, center_y = self.width - 105, 78
        radius = 44
        start = 90
        palette = {"A": ORANGE, "T": NAVY, "G": colors.HexColor("#E7A47D"), "C": colors.HexColor("#94A3B8")}
        for base in "ATGC":
            extent = self.composition.get(base, 0) * 3.6
            canvas.setFillColor(palette[base])
            canvas.wedge(center_x - radius, center_y - radius, center_x + radius, center_y + radius, start, extent, fill=1, stroke=0)
            start -= extent
        canvas.setFillColor(colors.white)
        canvas.circle(center_x, center_y, 25, fill=1, stroke=0)
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawCentredString(center_x, center_y + 2, f"{self.gc_content:.1f}%")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(center_x, center_y - 10, "GC CONTENT")

        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(20, 118, "Nucleotide composition")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(20, 103, "Measured across all valid FASTA bases")
        bar_x, bar_y, bar_width, bar_height = 20, 72, 220, 14
        cursor = bar_x
        for base in "ATGC":
            segment = bar_width * self.composition.get(base, 0) / 100
            canvas.setFillColor(palette[base])
            canvas.roundRect(cursor, bar_y, segment, bar_height, 3, fill=1, stroke=0)
            cursor += segment
        for index, base in enumerate("ATGC"):
            legend_x = 20 + (index % 2) * 110
            legend_y = 43 - (index // 2) * 17
            canvas.setFillColor(palette[base])
            canvas.circle(legend_x, legend_y + 3, 3, fill=1, stroke=0)
            canvas.setFillColor(NAVY)
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(legend_x + 9, legend_y, f"{base}  {self.composition.get(base, 0):.2f}%")


class CoverPage(Flowable):
    """Draw the branded report cover."""

    def __init__(self, filename: str, generated_at: str) -> None:
        super().__init__()
        self.filename = filename
        self.generated_at = generated_at
        self.width = PAGE_WIDTH - (2 * MARGIN)
        self.height = PAGE_HEIGHT - 120

    def draw(self) -> None:
        canvas = self.canv
        canvas.setFillColor(LIGHT)
        canvas.roundRect(0, 0, self.width, self.height, 14, fill=1, stroke=0)
        canvas.setFillColor(ORANGE)
        canvas.roundRect(0, self.height - 11, self.width, 11, 5, fill=1, stroke=0)
        canvas.setFillColor(ORANGE)
        _draw_logo(canvas, 68, self.height - 72, 25)
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawString(105, self.height - 67, "DeepGeneLens")
        canvas.setFillColor(colors.HexColor("#A05234"))
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(105, self.height - 82, "RESEARCH PROTOTYPE")
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 29)
        canvas.drawString(38, self.height - 175, "DNA Sequence")
        canvas.drawString(38, self.height - 211, "Analysis Report")
        canvas.setFillColor(ORANGE)
        canvas.rect(38, self.height - 237, 54, 3, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 13)
        canvas.drawString(38, self.height - 273, "AI-Powered Genomic Analysis")
        canvas.setFont("Helvetica", 10)
        canvas.drawString(38, self.height - 323, "A transparent research workflow for exploring")
        canvas.drawString(38, self.height - 340, "DNA composition, sequence quality, and experimental")
        canvas.drawString(38, self.height - 357, "viral-family classification.")
        canvas.setFillColor(colors.white)
        canvas.roundRect(38, 55, self.width - 76, 80, 8, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(55, 111, "UPLOADED FASTA FILE")
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(55, 91, _truncate(self.filename, 70))
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 9)
        canvas.drawString(55, 72, f"Generated {self.generated_at}")


def _draw_logo(canvas: Any, center_x: float, center_y: float, radius: float) -> None:
    """Draw the DeepGeneLens DNA-and-lens brand mark."""
    canvas.saveState()
    canvas.setFillColor(ORANGE)
    canvas.circle(center_x, center_y, radius, fill=1, stroke=0)
    canvas.setStrokeColor(colors.white)
    canvas.setLineWidth(1.7)
    left = center_x - radius * 0.34
    right = center_x + radius * 0.34
    top = center_y + radius * 0.62
    bottom = center_y - radius * 0.62
    canvas.bezier(left, top, right, center_y + radius * 0.3, left, center_y - radius * 0.3, right, bottom)
    canvas.bezier(right, top, left, center_y + radius * 0.3, right, center_y - radius * 0.3, left, bottom)
    for fraction in (0.25, 0.5, 0.75):
        y = top - (top - bottom) * fraction
        offset = radius * 0.27
        canvas.line(center_x - offset, y, center_x + offset, y)
    canvas.setLineWidth(1)
    canvas.circle(center_x, center_y, radius * 0.82, fill=0, stroke=1)
    canvas.restoreState()


class ResearchDocTemplate(BaseDocTemplate):
    """Document template with consistent branded footer and page numbers."""

    def __init__(self, output: BytesIO, **kwargs: Any) -> None:
        super().__init__(output, **kwargs)
        frame = Frame(MARGIN, 48, PAGE_WIDTH - 2 * MARGIN, PAGE_HEIGHT - 92, id="normal")
        self.addPageTemplates([PageTemplate(id="report", frames=frame, onPage=_draw_header_footer)])


def _draw_header_footer(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 32, PAGE_WIDTH - MARGIN, 32)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(MARGIN, 21, "DeepGeneLens  ·  RESEARCH PROTOTYPE  ·  NOT FOR CLINICAL USE")
    canvas.drawRightString(PAGE_WIDTH - MARGIN, 21, f"Page {document.page}")
    if document.page > 1:
        canvas.setFillColor(ORANGE)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(MARGIN, PAGE_HEIGHT - 31, "DEEPGENELENS / DNA ANALYSIS")
    canvas.restoreState()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("ReportTitle", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=NAVY, spaceAfter=8),
        "section": ParagraphStyle("Section", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=NAVY, spaceBefore=8, spaceAfter=8),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica", fontSize=9, leading=13, textColor=MUTED),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName="Helvetica", fontSize=7.5, leading=10, textColor=MUTED),
        "table": ParagraphStyle("Table", parent=base["BodyText"], fontName="Helvetica", fontSize=8, leading=10, textColor=NAVY),
        "table_header": ParagraphStyle("TableHeader", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=colors.white),
        "kpi": ParagraphStyle("Kpi", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=17, leading=19, textColor=NAVY, alignment=TA_CENTER),
        "kpi_label": ParagraphStyle("KpiLabel", parent=base["BodyText"], fontName="Helvetica", fontSize=7.5, leading=9, textColor=MUTED, alignment=TA_CENTER),
        "center": ParagraphStyle("Center", parent=base["BodyText"], fontName="Helvetica", fontSize=9, leading=13, textColor=MUTED, alignment=TA_CENTER),
    }


def build_analysis_pdf(
    filename: str,
    analysis: dict[str, object],
    predictions: list[dict[str, object]] | None = None,
    model_metadata: dict[str, object] | None = None,
) -> BytesIO:
    """Build a paginated, data-driven scientific report."""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    styles = _styles()
    output = BytesIO()
    document = ResearchDocTemplate(output, pagesize=letter, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=46, bottomMargin=48)
    story: list[Flowable] = [
        CoverPage(filename, generated_at),
        PageBreak(),
        Paragraph("Executive summary", styles["title"]),
        Paragraph("A concise view of the uploaded sequence set and its measured nucleotide properties.", styles["body"]),
        Spacer(1, 16),
        _kpi_table(analysis, styles),
        Spacer(1, 24),
        Paragraph("DNA composition analysis", styles["section"]),
        CompositionChart(analysis["composition"], float(analysis["gc_content"])),
        Spacer(1, 18),
        Paragraph("Sequence details", styles["section"]),
        _sequence_table(analysis["records"], styles),
    ]
    if predictions:
        story.extend([Spacer(1, 22), Paragraph("AI prediction results", styles["section"]), Paragraph("These outputs are generated by the installed experimental model and are not clinical conclusions.", styles["body"]), Spacer(1, 9), _prediction_table(predictions, styles)])
    story.extend([
        PageBreak(),
        Paragraph("Model information", styles["title"]),
        Paragraph("Experimental evaluation context", styles["section"]),
        Paragraph("The following values describe the trained research model and held-out evaluation snapshot. They are not the accuracy of an individual uploaded sequence prediction.", styles["body"]),
        Spacer(1, 14),
        _model_table(model_metadata, styles),
        Spacer(1, 24),
        _limitations_box(styles),
    ])
    document.build(story)
    output.seek(0)
    return output


def _kpi_table(analysis: dict[str, object], styles: dict[str, ParagraphStyle]) -> Table:
    valid = "VALID DNA" if analysis["valid"] else f"INVALID ({analysis['invalid_base_count']})"
    data = [[
        Paragraph(str(analysis["sequence_count"]), styles["kpi"]),
        Paragraph(f"{int(analysis['total_bases']):,}", styles["kpi"]),
        Paragraph(valid, styles["kpi"]),
        Paragraph(f"{float(analysis['gc_content']):.2f}%", styles["kpi"]),
    ], [
        Paragraph("TOTAL SEQUENCES", styles["kpi_label"]),
        Paragraph("TOTAL BASES", styles["kpi_label"]),
        Paragraph("VALIDATION STATUS", styles["kpi_label"]),
        Paragraph("OVERALL GC CONTENT", styles["kpi_label"]),
    ]]
    table = Table(data, colWidths=[1.25 * inch] * 4, rowHeights=[34, 24])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("BOX", (0, 0), (-1, -1), .5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), .5, colors.white), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TEXTCOLOR", (2, 0), (2, 0), GREEN if analysis["valid"] else colors.HexColor("#B54736")),
    ]))
    return table


def _sequence_table(records: object, styles: dict[str, ParagraphStyle]) -> Table:
    data = [[Paragraph("SEQUENCE ID", styles["table_header"]), Paragraph("LENGTH", styles["table_header"]), Paragraph("GC CONTENT", styles["table_header"]), Paragraph("STATUS", styles["table_header"])]]
    for record in records:
        data.append([Paragraph(_escape(str(record["id"])), styles["table"]), Paragraph(f"{int(record['length']):,} bases", styles["table"]), Paragraph(f"{float(record['gc_content']):.2f}%", styles["table"]), Paragraph("VALID", styles["table"])])
    table = Table(data, colWidths=[3.05 * inch, 1.25 * inch, 1.2 * inch, .9 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("BOX", (0, 0), (-1, -1), .5, BORDER), ("INNERGRID", (0, 0), (-1, -1), .35, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TEXTCOLOR", (3, 1), (3, -1), GREEN),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def _prediction_table(predictions: list[dict[str, object]], styles: dict[str, ParagraphStyle]) -> Table:
    data = [[Paragraph("SEQUENCE ID", styles["table_header"]), Paragraph("PREDICTED FAMILY", styles["table_header"]), Paragraph("CONFIDENCE", styles["table_header"]), Paragraph("STATUS", styles["table_header"])]]
    for prediction in predictions:
        data.append([Paragraph(_escape(str(prediction.get("sequence_id", ""))), styles["table"]), Paragraph(_escape(str(prediction.get("predicted_family", ""))), styles["table"]), Paragraph(f"{float(prediction.get('confidence', 0)) * 100:.2f}%", styles["table"]), Paragraph("RESEARCH OUTPUT", styles["table"])])
    table = Table(data, colWidths=[2.5 * inch, 1.75 * inch, 1.15 * inch, 1.0 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ORANGE), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("BOX", (0, 0), (-1, -1), .5, BORDER), ("INNERGRID", (0, 0), (-1, -1), .35, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TEXTCOLOR", (1, 1), (1, -1), ORANGE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def _model_table(metadata: dict[str, object] | None, styles: dict[str, ParagraphStyle]) -> Table:
    metadata = metadata or _load_model_metadata()
    metrics = metadata.get("test_metrics", {}) if isinstance(metadata.get("test_metrics", {}), dict) else {}
    model_type = metadata.get("model_type")
    class_count = metadata.get("class_count")
    max_length = metadata.get("max_length")
    accuracy = metrics.get("accuracy")
    f1_weighted = metrics.get("f1_weighted")
    rows = [
        ["Architecture", str(model_type) if model_type is not None else "Not available"],
        ["Classification classes", f"{class_count} viral families" if class_count is not None else "Not available"],
        ["Preprocessing", f"{max_length}-base input; A/C/G/T one-hot encoding" if max_length is not None else "Not available"],
        ["Held-out accuracy", f"{float(accuracy) * 100:.2f}%" if accuracy is not None else "Not available"],
        ["Weighted F1", f"{float(f1_weighted) * 100:.2f}%" if f1_weighted is not None else "Not available"],
        ["Evaluation status", "Experimental research metrics"],
    ]
    data = [[Paragraph("MODEL ATTRIBUTE", styles["table_header"]), Paragraph("VALUE", styles["table_header"])]]
    data.extend([[Paragraph(_escape(label), styles["table"]), Paragraph(_escape(value), styles["table"])] for label, value in rows])
    table = Table(data, colWidths=[2.1 * inch, 4.3 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT, colors.white]),
        ("BOX", (0, 0), (-1, -1), .5, BORDER), ("INNERGRID", (0, 0), (-1, -1), .35, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _load_model_metadata() -> dict[str, object]:
    metadata_path = Path(__file__).resolve().parents[3] / "artifacts" / "viral_family_cnn.metrics.json"
    try:
        with metadata_path.open(encoding="utf-8") as metadata_file:
            metadata = json.load(metadata_file)
    except FileNotFoundError:
        return {}
    if not isinstance(metadata, dict):
        return {}
    return metadata


def _limitations_box(styles: dict[str, ParagraphStyle]) -> Table:
    text = "DeepGeneLens is an experimental research prototype. Predictions are not clinically validated and must not be used for medical diagnosis or treatment decisions."
    table = Table([[Paragraph("<b>RESPONSIBLE RESEARCH NOTICE</b><br/>" + text, styles["body"])]], colWidths=[6.4 * inch])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF4EE")), ("BOX", (0, 0), (-1, -1), .7, ORANGE), ("PADDING", (0, 0), (-1, -1), 14)]))
    return table


def _escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _truncate(value: str, maximum: int) -> str:
    return value if len(value) <= maximum else value[: maximum - 3] + "..."
