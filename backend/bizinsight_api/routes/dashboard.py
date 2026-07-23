"""
Dashboard routes — pre-aggregated JSON for charts and metrics.
Replaces the Streamlit Dashboard tab computations.
"""

import os
import pandas as pd
from fastapi import APIRouter, HTTPException, Depends
from sklearn.feature_extraction.text import CountVectorizer

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from database import fetch_feedback
from bizinsight_api.routes.auth import get_current_user
from bizinsight_api.models.schemas import (
    DashboardSummary, TrendPoint, KeywordItem, AlertStatus
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(current_user: dict = Depends(get_current_user)):
    """
    Return all dashboard metrics in a single payload:
    counts, percentages, trend data, and top keywords.
    """
    data = fetch_feedback(user_id=current_user["id"])

    if not data:
        return DashboardSummary(
            total_reviews=0,
            positive_count=0,
            negative_count=0,
            neutral_count=0,
            positive_percent=0.0,
            negative_percent=0.0,
            neutral_percent=0.0,
            avg_sentiment=0.0,
            trend=[],
            top_keywords=[],
        )

    df = pd.DataFrame(data, columns=["review", "sentiment", "date"])
    df["date"] = pd.to_datetime(df["date"])

    total = len(df)
    positive = int((df["sentiment"] > 0).sum())
    negative = int((df["sentiment"] < 0).sum())
    neutral = int((df["sentiment"] == 0).sum())

    positive_pct = round((positive / total) * 100, 2)
    negative_pct = round((negative / total) * 100, 2)
    neutral_pct = round((neutral / total) * 100, 2)
    avg_sentiment = round(df["sentiment"].mean(), 4)

    # Trend — average sentiment per day
    trend_df = df.groupby(df["date"].dt.date)["sentiment"].mean().reset_index()
    trend_df.columns = ["date", "avg_sentiment"]
    trend = [
        TrendPoint(date=str(row["date"]), avg_sentiment=round(row["avg_sentiment"], 4))
        for _, row in trend_df.iterrows()
    ]

    # Top keywords
    reviews = df["review"].dropna()
    keywords_list = []
    if not reviews.empty:
        try:
            vectorizer = CountVectorizer(stop_words="english", max_features=10)
            X = vectorizer.fit_transform(reviews)
            kw_names = vectorizer.get_feature_names_out()
            kw_counts = X.toarray().sum(axis=0)
            keywords_list = [
                KeywordItem(keyword=str(name), frequency=int(count))
                for name, count in zip(kw_names, kw_counts)
            ]
        except ValueError:
            pass

    return DashboardSummary(
        total_reviews=total,
        positive_count=positive,
        negative_count=negative,
        neutral_count=neutral,
        positive_percent=positive_pct,
        negative_percent=negative_pct,
        neutral_percent=neutral_pct,
        avg_sentiment=avg_sentiment,
        trend=trend,
        top_keywords=keywords_list,
    )


@router.get("/alerts", response_model=AlertStatus)
def alerts_current(current_user: dict = Depends(get_current_user)):
    """
    Return the current risk level based on negative sentiment percentage.
    Mirrors the alert logic from the original app.py.
    """
    data = fetch_feedback(user_id=current_user["id"])

    if not data:
        return AlertStatus(
            risk_level="low",
            negative_percent=0.0,
            total_reviews=0,
            top_issues=[],
        )

    df = pd.DataFrame(data, columns=["review", "sentiment", "date"])
    total = len(df)
    negative = int((df["sentiment"] < 0).sum())
    negative_pct = round((negative / total) * 100, 2) if total > 0 else 0

    # Top issues from negative reviews
    neg_reviews = df[df["sentiment"] < 0]["review"].dropna()
    top_issues = []
    if not neg_reviews.empty:
        try:
            vectorizer = CountVectorizer(stop_words="english", max_features=5)
            X = vectorizer.fit_transform(neg_reviews)
            top_issues = list(vectorizer.get_feature_names_out())
        except ValueError:
            pass

    # Risk level thresholds (same as original app.py)
    ALERT_THRESHOLD = 40.0
    if negative_pct >= ALERT_THRESHOLD:
        risk_level = "high"
    elif negative_pct >= 25:
        risk_level = "medium"
    else:
        risk_level = "low"

    return AlertStatus(
        risk_level=risk_level,
        negative_percent=negative_pct,
        total_reviews=total,
        top_issues=top_issues,
        threshold=ALERT_THRESHOLD,
    )
