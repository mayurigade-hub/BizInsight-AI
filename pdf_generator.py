import io

import matplotlib.pyplot as plt

from reportlab.platypus import SimpleDocTemplate, Paragraph, Image
from reportlab.lib.styles import getSampleStyleSheet


from datetime import datetime

# ------------------------------------------------------------------
# Shared PDF report helpers
# Reused across different PDF generation implementations.
# ------------------------------------------------------------------

def get_report_timestamp():
    """
    Generate a consistent timestamp for all PDF reports.
    """
    return datetime.now().strftime("%d-%m-%Y %H:%M")


def generate_summary(positive, negative):
    """
    Generate a high-level sentiment summary.
    """
    if positive > negative:
        return "Overall customer sentiment is favorable."

    return "Customer feedback indicates improvement areas in service."


def generate_insight(positive, negative):
    """
    Generate key business insight based on sentiment distribution.
    """
    if positive > negative:
        return (
            "Customer sentiment is mostly positive. "
            "Customers appear satisfied with the service experience."
        )

    return (
        "Negative sentiment is higher than positive sentiment. "
        "This suggests improvements are needed in customer experience."
    )


def generate_recommendation(positive, negative):
    """
    Generate actionable recommendation based on sentiment analysis.
    """
    if negative > positive:
        return (
            "Focus on resolving recurring complaints and improving "
            "customer support response time."
        )

    return (
        "Maintain current service quality and continue monitoring "
        "customer satisfaction trends."
    )

# ------------------------------------------------------------------
# Streamlit analytics report generator
# Centralized PDF generation service used by dashboard exports
# ------------------------------------------------------------------

   
def generate_report_pdf(df, trend, keywords):
    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("BizInsight AI Report", styles["Title"]))
    content.append(Paragraph("Generated: " + get_report_timestamp(), styles["Normal"]))
    content.append(Paragraph("Total Reviews: " + str(len(df)), styles["Normal"]))
    content.append(Paragraph("Positive: " + str((df["sentiment"] > 0).sum()), styles["Normal"]))
    content.append(Paragraph("Negative: " + str((df["sentiment"] < 0).sum()), styles["Normal"]))

    fig1, ax1 = plt.subplots()
    ax1.plot(trend.index, trend.values)
    ax1.set_title("Sentiment Trend")
    img1 = io.BytesIO()
    fig1.savefig(img1, format="png")
    plt.close(fig1)
    img1.seek(0)
    content.append(Image(img1, width=400, height=200))

    fig2, ax2 = plt.subplots()
    ax2.bar(["Positive", "Negative"], [(df["sentiment"] > 0).sum(), (df["sentiment"] < 0).sum()])
    ax2.set_title("Positive vs Negative")
    img2 = io.BytesIO()
    fig2.savefig(img2, format="png")
    plt.close(fig2)
    img2.seek(0)
    content.append(Image(img2, width=400, height=200))

    content.append(Paragraph("Top Keywords: " + ", ".join(keywords), styles["Normal"]))
    pdf.build(content)
    buffer.seek(0)
    return buffer.read() 

