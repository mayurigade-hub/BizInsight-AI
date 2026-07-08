import ast
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from sklearn.feature_extraction.text import CountVectorizer
from business_insights import render_business_insights
from business_insights import build_business_summary


ASPECTS = [
    "Product Quality",
    "Price",
    "Delivery",
    "Packaging",
    "Customer Service",
]


def normalize_aspect_sentiment(value):
    """
    Converts stored strings back to dictionaries if required.
    """

    if isinstance(value, dict):
        return value

    if isinstance(value, str):

        try:
            return ast.literal_eval(value)
        except Exception:
            return {}

    return {}


def build_aspect_summary(df):

    rows = []

    for aspect in ASPECTS:

        pos = neu = neg = 0

        for sentiment in df["aspect_sentiment"]:

            sentiment = normalize_aspect_sentiment(sentiment)

            if aspect not in sentiment:
                continue

            if sentiment[aspect] == "Positive":
                pos += 1

            elif sentiment[aspect] == "Negative":
                neg += 1

            else:
                neu += 1

        rows.append(
            {
                "Aspect": aspect,
                "Positive": pos,
                "Neutral": neu,
                "Negative": neg,
                "Total": pos + neu + neg,
            }
        )

    return pd.DataFrame(rows)


def show_kpis(summary):

    st.subheader("📈 Aspect KPIs")

    total_mentions = summary["Total"].sum()
    total_positive = summary["Positive"].sum()
    total_negative = summary["Negative"].sum()
    total_neutral = summary["Neutral"].sum()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Aspect Mentions", total_mentions)
    c2.metric("Positive", total_positive)
    c3.metric("Negative", total_negative)
    c4.metric("Neutral", total_neutral)


def show_summary_table(summary):

    st.subheader("📊 Aspect-wise Sentiment Summary")

    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True,
    )

def plot_stacked_chart(summary):
    """
    Plot aspect-wise stacked sentiment chart.
    """

    st.subheader("📊 Aspect-wise Sentiment Distribution")

    fig, ax = plt.subplots(figsize=(10, 5))

    x = range(len(summary))

    positive = summary["Positive"]
    neutral = summary["Neutral"]
    negative = summary["Negative"]

    ax.bar(
        x,
        positive,
        label="Positive"
    )

    ax.bar(
        x,
        neutral,
        bottom=positive,
        label="Neutral"
    )

    ax.bar(
        x,
        negative,
        bottom=positive + neutral,
        label="Negative"
    )

    ax.set_xticks(list(x))
    ax.set_xticklabels(
        summary["Aspect"],
        rotation=20,
        ha="right"
    )

    ax.set_ylabel("Number of Reviews")
    ax.set_title("Aspect-wise Sentiment Distribution")
    ax.legend()

    st.pyplot(fig)

    plt.close(fig)


def show_negative_ranking(summary):
    """
    Show aspects ranked by negative sentiment.
    """

    st.subheader("🚨 Most Critical Aspects")

    ranking = (
        summary.sort_values(
            "Negative",
            ascending=False
        )
        .reset_index(drop=True)
    )

    ranking.index += 1

    st.dataframe(
        ranking[
            [
                "Aspect",
                "Negative",
                "Total"
            ]
        ],
        use_container_width=True
    )


def plot_aspect_pie(df, aspect):
    """
    Pie chart for selected aspect.
    """

    positive = 0
    neutral = 0
    negative = 0

    for sentiment in df["aspect_sentiment"]:

        sentiment = normalize_aspect_sentiment(sentiment)

        if aspect not in sentiment:
            continue

        value = sentiment[aspect]

        if value == "Positive":
            positive += 1

        elif value == "Negative":
            negative += 1

        else:
            neutral += 1

    fig, ax = plt.subplots(figsize=(4, 4))

    ax.pie(
        [positive, neutral, negative],
        labels=[
            "Positive",
            "Neutral",
            "Negative"
        ],
        autopct="%1.1f%%",
        startangle=90
    )

    ax.set_title(f"{aspect} Sentiment")

    st.pyplot(fig)

    plt.close(fig)

def show_aspect_details(df):
    """
    Interactive aspect explorer.
    """

    st.subheader("🔍 Aspect Explorer")

    selected_aspect = st.selectbox(
        "Choose an Aspect",
        ASPECTS
    )

    filtered_rows = []

    for _, row in df.iterrows():

        sentiment = normalize_aspect_sentiment(
            row["aspect_sentiment"]
        )

        if selected_aspect not in sentiment:
            continue

        filtered_rows.append(
            {
                "Review": row["review"],
                "Aspect Sentiment": sentiment[selected_aspect],
                "Overall Sentiment Score": round(row["sentiment"], 3)
            }
        )

    if not filtered_rows:
        st.info(f"No reviews found for **{selected_aspect}**.")
        return

    filtered_df = pd.DataFrame(filtered_rows)

    # KPI cards
    positive = (
        filtered_df["Aspect Sentiment"] == "Positive"
    ).sum()

    neutral = (
        filtered_df["Aspect Sentiment"] == "Neutral"
    ).sum()

    negative = (
        filtered_df["Aspect Sentiment"] == "Negative"
    ).sum()

    total = len(filtered_df)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Reviews", total)
    c2.metric("Positive", positive)
    c3.metric("Neutral", neutral)
    c4.metric("Negative", negative)

    st.markdown("---")

    left, right = st.columns([2, 1])

    with left:

        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )

    with right:

        plot_aspect_pie(df, selected_aspect)

    st.markdown("---")

    st.subheader("🏷 Top Keywords")

    reviews = filtered_df["Review"]

    if len(reviews):

        vectorizer = CountVectorizer(
            stop_words="english",
            max_features=10
        )

        X = vectorizer.fit_transform(reviews)

        words = vectorizer.get_feature_names_out()

        counts = X.toarray().sum(axis=0)

        keyword_df = (
            pd.DataFrame(
                {
                    "Keyword": words,
                    "Frequency": counts
                }
            )
            .sort_values(
                "Frequency",
                ascending=False
            )
        )

        st.dataframe(
            keyword_df,
            use_container_width=True,
            hide_index=True
        )


def render_aspect_dashboard(df):
    """
    Main Aspect Dashboard
    """

    if "aspect_sentiment" not in df.columns:
        st.warning(
            "Aspect sentiment data not available."
        )
        return

    summary = build_aspect_summary(df)

    business_summary = build_business_summary(summary)

    render_business_insights(business_summary)

    st.markdown("---")

    st.header("📊 Aspect Analytics Dashboard")

    show_kpis(summary)

    st.markdown("---")

    show_summary_table(summary)

    st.markdown("---")

    plot_stacked_chart(summary)

    st.markdown("---")

    show_negative_ranking(summary)

    st.markdown("---")

    show_aspect_details(df)