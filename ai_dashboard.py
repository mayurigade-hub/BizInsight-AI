import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt


def extract_confidence(aspect_data):

    confidences = []

    for value in aspect_data.values():

        if isinstance(value, dict):

            confidences.append(value["confidence"])

    return confidences


def build_confidence_dataframe(df):

    rows = []

    for _, row in df.iterrows():

        if not isinstance(row["aspect_sentiment"], dict):
            continue

        for aspect, value in row["aspect_sentiment"].items():

            if not isinstance(value, dict):
                continue

            rows.append(
                {
                    "Review": row["review"],
                    "Aspect": aspect,
                    "Sentiment": value["sentiment"],
                    "Confidence": value["confidence"]
                }
            )

    return pd.DataFrame(rows)

def show_confidence_metrics(conf_df):

    st.subheader("🤖 AI Confidence")

    if conf_df.empty:
        st.info("No AI predictions available.")
        return

    avg = round(conf_df["Confidence"].mean() * 100, 1)

    high = (conf_df["Confidence"] >= 0.8).sum()

    low = (conf_df["Confidence"] < 0.8).sum()

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Average Confidence",
        f"{avg}%"
    )

    c2.metric(
        "High Confidence",
        high
    )

    c3.metric(
        "Needs Review",
        low
    )

def confidence_chart(conf_df):

    st.subheader("📊 Confidence Distribution")

    if conf_df.empty:
        return

    fig, ax = plt.subplots(figsize=(6,4))

    ax.hist(
        conf_df["Confidence"],
        bins=10
    )

    ax.set_xlabel("Confidence")

    ax.set_ylabel("Predictions")

    st.pyplot(fig)

    plt.close(fig)

def manual_review_queue(conf_df):

    st.subheader("⚠ Manual Review Queue")

    queue = conf_df[
        conf_df["Confidence"] < 0.80
    ]

    if queue.empty:

        st.success(
            "No reviews require manual verification."
        )

        return

    st.dataframe(
        queue,
        use_container_width=True,
        hide_index=True
    )

def render_ai_dashboard(df):

    conf_df = build_confidence_dataframe(df)

    show_confidence_metrics(conf_df)

    st.markdown("---")

    confidence_chart(conf_df)

    st.markdown("---")

    manual_review_queue(conf_df)

