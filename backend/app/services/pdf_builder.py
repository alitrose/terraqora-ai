from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Brand Color Palette
COLOR_FOREST_DEEP = HexColor("#123524")
COLOR_LEAF_EMERALD = HexColor("#2E7D32")
COLOR_HARVEST_GOLD = HexColor("#C9972C")
COLOR_GOLD_LIGHT = HexColor("#FDF9EF")
COLOR_PARCHMENT = HexColor("#F7F5EE")
COLOR_CHARCOAL = HexColor("#222222")
COLOR_MUTED = HexColor("#555555")
COLOR_BORDER = HexColor("#E2E8F0")
COLOR_WHITE = HexColor("#FFFFFF")
COLOR_ALERT_BG = HexColor("#FFF8E1")
COLOR_ALERT_BORDER = HexColor("#FFE082")


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute total pages and draw consistent header/footer."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.pages: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        page_count = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_header_footer(page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_header_footer(self, page_count: int) -> None:
        self.saveState()

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(COLOR_FOREST_DEEP)
            self.drawString(54, 755, "TERRAQORA AI")
            self.setFont("Helvetica", 8)
            self.setFillColor(COLOR_MUTED)
            self.drawString(125, 755, "|  Intelligence for Every Acre  •  Farm Intelligence Report")
            self.setStrokeColor(COLOR_BORDER)
            self.setLineWidth(0.5)
            self.line(54, 747, 612 - 54, 747)

        # Running Footer (all pages)
        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.5)
        self.line(54, 46, 612 - 54, 46)

        self.setFont("Helvetica", 7.5)
        self.setFillColor(COLOR_MUTED)
        self.drawString(
            54,
            34,
            "Confidential Agronomic Intelligence  •  Verify field diagnosis & inputs with local KVK / ICAR extension officers.",
        )
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 54, 34, page_str)

        self.restoreState()


def _get_report_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()

    styles = {
        "BrandTitle": ParagraphStyle(
            "BrandTitle",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=COLOR_FOREST_DEEP,
        ),
        "BrandTagline": ParagraphStyle(
            "BrandTagline",
            parent=sample["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            textColor=COLOR_HARVEST_GOLD,
        ),
        "ReportTitle": ParagraphStyle(
            "ReportTitle",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=COLOR_FOREST_DEEP,
            spaceAfter=6,
        ),
        "SectionHeading": ParagraphStyle(
            "SectionHeading",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=COLOR_FOREST_DEEP,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=COLOR_CHARCOAL,
        ),
        "BodyBold": ParagraphStyle(
            "BodyBold",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11.5,
            textColor=COLOR_CHARCOAL,
        ),
        "CalloutTitle": ParagraphStyle(
            "CalloutTitle",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12.5,
            textColor=COLOR_FOREST_DEEP,
        ),
        "CalloutBody": ParagraphStyle(
            "CalloutBody",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=COLOR_CHARCOAL,
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=COLOR_WHITE,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=COLOR_CHARCOAL,
        ),
        "TableCellBold": ParagraphStyle(
            "TableCellBold",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10.5,
            textColor=COLOR_CHARCOAL,
        ),
        "Disclaimers": ParagraphStyle(
            "Disclaimers",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9.5,
            textColor=COLOR_MUTED,
        ),
    }
    return styles


def build_agronomic_pdf(report_data: dict[str, Any]) -> bytes:
    """Renders a complete, professional, publication-quality agronomic PDF using ReportLab."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = _get_report_styles()
    story: list[Any] = []

    # 1. Header & Brand Block
    header_left = [
        Paragraph("TERRAQORA AI", styles["BrandTitle"]),
        Paragraph("Intelligence for Every Acre.", styles["BrandTagline"]),
    ]
    gen_dt = report_data.get("generation_date") or datetime.now().strftime("%B %d, %Y • %H:%M UTC")
    ref_id = str(report_data.get("reference_id", "TQ-REPORT-001"))[:18]

    header_right = [
        Paragraph(f"<b>Report Ref:</b> {ref_id}", styles["TableCellBold"]),
        Paragraph(f"<b>Generated:</b> {gen_dt}", styles["TableCell"]),
        Paragraph(f"<b>Farmer:</b> {report_data.get('farmer_name', 'TerraQora Farmer')}", styles["TableCell"]),
    ]

    header_table = Table(
        [[header_left, header_right]],
        colWidths=[3.2 * inch, 3.8 * inch],
    )
    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ])
    )
    story.append(header_table)
    story.append(Spacer(1, 8))
    story.append(
        HRFlowable(width="100%", thickness=1.5, color=COLOR_FOREST_DEEP, spaceBefore=2, spaceAfter=8)
    )

    # 2. Document Title
    doc_title = report_data.get("title", "Farm Intelligence & Advisory Report")
    story.append(Paragraph(doc_title, styles["ReportTitle"]))

    # 3. Farm Profile Summary (if linked)
    farm = report_data.get("farm")
    if farm:
        coords_str = (
            f"({farm.get('latitude', 0.0):.3f}°N, {farm.get('longitude', 0.0):.3f}°E)"
            if farm.get("latitude") is not None
            else "Not specified"
        )
        farm_info_data = [
            [
                Paragraph("<b>Farm Plot:</b>", styles["TableCellBold"]),
                Paragraph(str(farm.get("name", "Plot")), styles["TableCell"]),
                Paragraph("<b>Location:</b>", styles["TableCellBold"]),
                Paragraph(f"{farm.get('district', '')}, {farm.get('state', '')}", styles["TableCell"]),
            ],
            [
                Paragraph("<b>Area:</b>", styles["TableCellBold"]),
                Paragraph(f"{farm.get('area_hectares', 'N/A')} hectares", styles["TableCell"]),
                Paragraph("<b>GPS Coordinates:</b>", styles["TableCellBold"]),
                Paragraph(coords_str, styles["TableCell"]),
            ],
            [
                Paragraph("<b>Soil Type & pH:</b>", styles["TableCellBold"]),
                Paragraph(f"{farm.get('soil_type', 'N/A')} (pH {farm.get('soil_ph', 'N/A')})", styles["TableCell"]),
                Paragraph("<b>Primary Crop:</b>", styles["TableCellBold"]),
                Paragraph(f"{farm.get('primary_crop', 'N/A')} ({farm.get('irrigation_type', 'N/A')})", styles["TableCell"]),
            ],
        ]
        farm_table = Table(farm_info_data, colWidths=[1.1 * inch, 2.4 * inch, 1.2 * inch, 2.3 * inch])
        farm_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_PARCHMENT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        story.append(farm_table)
        story.append(Spacer(1, 8))

    # 4. Executive Summary Callout Box
    ai_summary = report_data.get("ai_summary") or report_data.get("executive_summary")
    if ai_summary:
        summary_cells = [
            [Paragraph("EXECUTIVE AGRONOMIC SUMMARY", styles["CalloutTitle"])],
            [Paragraph(ai_summary, styles["CalloutBody"])],
        ]
        summary_table = Table(summary_cells, colWidths=[7.0 * inch])
        summary_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_GOLD_LIGHT),
                ("BOX", (0, 0), (-1, -1), 1, COLOR_HARVEST_GOLD),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(summary_table)
        story.append(Spacer(1, 10))

    # 5. Core Content Sections (Tables & Findings)
    sections = report_data.get("sections", [])
    for sec in sections:
        sec_title = sec.get("title", "Advisory Module")
        story.append(Paragraph(sec_title.upper(), styles["SectionHeading"]))

        # Optional Model Version Badge
        m_info = sec.get("model_info")
        if m_info:
            m_text = (
                f"<b>Algorithm:</b> {m_info.get('model_name', 'TerraQora ML')}  |  "
                f"<b>Version:</b> {m_info.get('model_version', 'v1.0')}  |  "
                f"<b>Validation:</b> {m_info.get('metrics_summary', 'Benchmarked')}"
            )
            story.append(Paragraph(m_text, styles["Disclaimers"]))
            story.append(Spacer(1, 3))

        # Data Table
        table_rows = sec.get("data_table")
        if table_rows:
            formatted_table_rows = []
            for r_idx, row in enumerate(table_rows):
                new_row = []
                for c_idx, cell in enumerate(row):
                    if r_idx == 0:
                        new_row.append(Paragraph(str(cell), styles["TableHeader"]))
                    elif c_idx == 0:
                        new_row.append(Paragraph(str(cell), styles["TableCellBold"]))
                    else:
                        new_row.append(Paragraph(str(cell), styles["TableCell"]))
                formatted_table_rows.append(new_row)

            n_cols = len(table_rows[0])
            col_w = (7.0 * inch) / max(1, n_cols)
            d_table = Table(formatted_table_rows, colWidths=[col_w] * n_cols)
            d_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_FOREST_DEEP),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ])
            )
            story.append(d_table)
            story.append(Spacer(1, 4))

        # Observations & Next Steps
        obs = sec.get("observations", [])
        for item in obs:
            bullet_p = Paragraph(f"• {item}", styles["Body"])
            story.append(bullet_p)

        story.append(Spacer(1, 6))

    # 6. Methodology & Disclosures Block
    disclosures = report_data.get("methodology_and_disclosures", [])
    if disclosures:
        disc_flowables = [
            Paragraph("DATA SOURCES & METHODOLOGY DISCLOSURES", styles["SectionHeading"]),
        ]
        for d in disclosures:
            disc_flowables.append(Paragraph(f"• {d}", styles["Disclaimers"]))
        story.append(KeepTogether(disc_flowables))
        story.append(Spacer(1, 6))

    # 7. Limitations & Uncertainty Warnings Box
    limitations = report_data.get("limitations_and_uncertainty", [])
    if limitations:
        alert_rows = [
            [Paragraph("IMPORTANT LIMITATIONS & DECISION-SUPPORT NOTICE", styles["CalloutTitle"])],
        ]
        for lim in limitations:
            alert_rows.append([Paragraph(f"• {lim}", styles["CalloutBody"])])

        alert_table = Table(alert_rows, colWidths=[7.0 * inch])
        alert_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_ALERT_BG),
                ("BOX", (0, 0), (-1, -1), 0.75, COLOR_ALERT_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(KeepTogether([alert_table]))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()
