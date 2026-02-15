"""월말 정산 리포트 PDF 생성"""
from datetime import date
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 한글 폰트 대체: 기본 Helvetica 사용 (한글 미지원 시 깨짐). 사용 시 system font 등록 필요
# pdfmetrics.registerFont(TTFont('Malgun', 'malgun.ttf'))


def _money_fmt(d: Decimal | None) -> str:
    if d is None:
        return "0"
    return f"{d:,.0f}"


def generate_monthly_report_pdf(
    plan_date_from: date,
    plan_date_to: date,
    completions: list,
    summary_by_driver: dict,
) -> BytesIO:
    """월말 정산 리포트 PDF 생성"""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm)
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph(
        f"<b>월말 정산 리포트</b><br/>"
        f"{plan_date_from} ~ {plan_date_to}",
        styles["Title"],
    )
    story.append(title)
    story.append(Spacer(1, 12))

    # 기사별 요약
    if summary_by_driver:
        driver_data = [["기사", "완료 스탑 수", "비고"]]
        for name, data in summary_by_driver.items():
            driver_data.append([name, str(data.get("count", 0)), data.get("memo", "")])
        t = Table(driver_data)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ]
            )
        )
        story.append(Paragraph("<b>기사별 완료 현황</b>", styles["Heading2"]))
        story.append(Spacer(1, 6))
        story.append(t)
        story.append(Spacer(1, 12))

    # 완료 목록
    if completions:
        comp_data = [["일자", "루트", "거래처", "기사", "완료시각"]]
        for c in completions:
            comp_data.append(
                [
                    str(c.get("plan_date", "")),
                    c.get("route_name", ""),
                    c.get("customer_name", ""),
                    c.get("driver_name", ""),
                    str(c.get("completed_at", ""))[:19] if c.get("completed_at") else "",
                ]
            )
        t2 = Table(comp_data)
        t2.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ]
            )
        )
        story.append(Paragraph("<b>완료 내역</b>", styles["Heading2"]))
        story.append(Spacer(1, 6))
        story.append(t2)

    doc.build(story)
    buf.seek(0)
    return buf
