import pandas as pd
import streamlit as st

ASPECTS = [
    "Product Quality",
    "Price",
    "Delivery",
    "Packaging",
    "Customer Service",
]


def calculate_health_score(positive, neutral, negative):
    """
    Returns a health score out of 100.
    """

    total = positive + neutral + negative

    if total == 0:
        return 100

    score = (
        (positive * 100)
        + (neutral * 50)
        + (negative * 0)
    ) / total

    return round(score, 1)


def health_status(score):

    if score >= 80:
        return "🟢 Excellent"

    if score >= 60:
        return "🟡 Good"

    if score >= 40:
        return "🟠 Needs Attention"

    return "🔴 Critical"


def build_business_summary(summary_df):

    rows = []

    for _, row in summary_df.iterrows():

        score = calculate_health_score(
            row["Positive"],
            row["Neutral"],
            row["Negative"]
        )

        rows.append(
            {
                "Aspect": row["Aspect"],
                "Health Score": score,
                "Status": health_status(score),
                "Positive": row["Positive"],
                "Neutral": row["Neutral"],
                "Negative": row["Negative"],
                "Total": row["Total"],
            }
        )

    return pd.DataFrame(rows)

def show_health_cards(summary):

    st.subheader("📈 Aspect Health")

    cols = st.columns(len(summary))

    for i, row in summary.iterrows():

        with cols[i]:

            st.metric(
                row["Aspect"],
                f'{row["Health Score"]}/100'
            )

            st.caption(row["Status"])

def show_priority_table(summary):

    st.subheader("🚨 Priority Ranking")

    priority = summary.sort_values(
        "Health Score"
    )

    priority = priority[
        [
            "Aspect",
            "Health Score",
            "Status"
        ]
    ]

    st.dataframe(
        priority,
        hide_index=True,
        use_container_width=True
    )

def generate_executive_summary(summary):
    """
    Generate a rule-based executive summary.
    """

    if summary.empty:
        st.info("No aspect data available.")
        return

    worst = summary.loc[summary["Health Score"].idxmin()]
    best = summary.loc[summary["Health Score"].idxmax()]

    st.subheader("📋 Executive Summary")

    st.info(
        f"""
**Overall Findings**

• **{worst['Aspect']}** is the weakest performing aspect with a health score of **{worst['Health Score']}/100**.

• **{best['Aspect']}** is the strongest aspect with a health score of **{best['Health Score']}/100**.

• Customers are generally happiest with **{best['Aspect']}**.

• The highest business priority should be improving **{worst['Aspect']}**.
"""
    )

def generate_alerts(summary):

    st.subheader("🚨 Business Alerts")

    alerts = 0

    for _, row in summary.iterrows():

        if row["Health Score"] < 40:

            st.error(
                f"{row['Aspect']} requires immediate attention."
            )

            alerts += 1

        elif row["Health Score"] < 60:

            st.warning(
                f"{row['Aspect']} should be monitored."
            )

            alerts += 1

    if alerts == 0:

        st.success(
            "No critical issues detected."
        )

RECOMMENDATIONS = {

    "Delivery": [
        "Investigate courier delays.",
        "Improve dispatch efficiency.",
        "Provide proactive shipment updates."
    ],

    "Price": [
        "Review pricing strategy.",
        "Introduce promotional offers.",
        "Highlight value for money."
    ],

    "Packaging": [
        "Continue maintaining packaging quality.",
        "Improve eco-friendly packaging."
    ],

    "Customer Service": [
        "Reduce response times.",
        "Provide additional staff training.",
        "Improve complaint resolution."
    ],

    "Product Quality": [
        "Strengthen quality inspections.",
        "Monitor recurring product defects.",
        "Improve manufacturing consistency."
    ]
}


def show_recommendations(summary):

    st.subheader("💡 Recommendations")

    ordered = summary.sort_values("Health Score")

    for _, row in ordered.iterrows():

        st.markdown(
            f"### {row['Aspect']}"
        )

        if row["Aspect"] in RECOMMENDATIONS:

            for recommendation in RECOMMENDATIONS[row["Aspect"]]:

                st.write(
                    f"• {recommendation}"
                )

        st.markdown("---")

def show_positive_highlights(summary):

    st.subheader("🎉 Positive Highlights")

    good = summary[
        summary["Health Score"] >= 80
    ]

    if good.empty:

        st.info(
            "No outstanding strengths detected."
        )

        return

    for _, row in good.iterrows():

        st.success(
            f"{row['Aspect']} is performing very well."
        )

def render_business_insights(summary):

    st.header("🧠 Business Insights")

    show_health_cards(summary)

    st.markdown("---")

    generate_executive_summary(summary)

    st.markdown("---")

    generate_alerts(summary)

    st.markdown("---")

    show_priority_table(summary)

    st.markdown("---")

    show_recommendations(summary)

    st.markdown("---")

    show_positive_highlights(summary)

