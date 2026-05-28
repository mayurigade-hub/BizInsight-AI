from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import TypedDict

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

DB_NAME = "bizinsight.db"


class AlertResult(TypedDict):
    risk_score: str
    risk_level: int
    spike_detected: bool
    recent_negative_pct: float
    baseline_negative_pct: float
    spike_delta: float
    top_risk_keywords: list[str]
    recent_count: int
    baseline_count: int
    insufficient_data: bool


WINDOW_DAYS = 7
BASELINE_DAYS = 7
MIN_REVIEWS = 5
HIGH_THRESHOLD_PCT = 60
MEDIUM_THRESHOLD_PCT = 40
SPIKE_THRESHOLD = 15
TOP_N_KEYWORDS = 8


def _empty_alert_result() -> AlertResult:
    """Return a safe default alert payload when data cannot be loaded."""
    return {
        "risk_score": "Low",
        "risk_level": 0,
        "spike_detected": False,
        "recent_negative_pct": 0.0,
        "baseline_negative_pct": 0.0,
        "spike_delta": 0.0,
        "top_risk_keywords": [],
        "recent_count": 0,
        "baseline_count": 0,
        "insufficient_data": True,
    }


def _fetch_windowed_reviews(window_days: int, offset_days: int = 0) -> pd.DataFrame:
    """
    Fetch reviews from a rolling window.

    Args:
        window_days: Number of days included in the window.
        offset_days: Number of days before now where the window ends.

    Returns:
        A dataframe containing review text, sentiment score, and timestamp.
    """
    now = datetime.now(timezone.utc)
    end = now - timedelta(days=offset_days)
    start = end - timedelta(days=window_days)

    conn = sqlite3.connect(DB_NAME)
    try:
        return pd.read_sql_query(
            """
            SELECT original_review AS review, sentiment, created_at
            FROM feedback
            WHERE created_at >= ?
              AND created_at < ?
            ORDER BY created_at DESC
            """,
            conn,
            params=(
                start.strftime("%Y-%m-%d %H:%M:%S"),
                end.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
    finally:
        conn.close()


def _negative_pct(df: pd.DataFrame) -> float:
    """Return the percentage of rows with negative sentiment."""
    if df.empty:
        return 0.0
    negative_count = int((df["sentiment"] < 0).sum())
    return float(round(negative_count / len(df) * 100, 1))


def _extract_risk_keywords(negative_reviews: list[str], n: int = TOP_N_KEYWORDS) -> list[str]:
    """
    Extract recurring terms from negative reviews using TF-IDF.

    Args:
        negative_reviews: Recent negative review texts.
        n: Maximum number of keywords or phrases to return.

    Returns:
        Top risk keywords and short phrases.
    """
    if len(negative_reviews) < 2:
        return []

    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=n,
        ngram_range=(1, 2),
        min_df=1,
    )
    try:
        vectorizer.fit_transform(negative_reviews)
        return list(vectorizer.get_feature_names_out())
    except ValueError:
        return []


def _compute_risk_score(negative_pct: float, spike_delta: float) -> tuple[str, int]:
    """
    Convert negative review percentage and spike delta into a risk label.

    Args:
        negative_pct: Percent of recent reviews with negative sentiment.
        spike_delta: Percentage-point change compared with the baseline window.

    Returns:
        A risk label and numeric risk level.
    """
    if negative_pct >= HIGH_THRESHOLD_PCT or spike_delta >= SPIKE_THRESHOLD * 2:
        return "High", 2
    if negative_pct >= MEDIUM_THRESHOLD_PCT or spike_delta >= SPIKE_THRESHOLD:
        return "Medium", 1
    return "Low", 0


def compute_alerts() -> AlertResult:
    """
    Compute the current trend alert state for the dashboard.

    Returns:
        Alert metadata including risk score, spike detection, and risk keywords.
    """
    try:
        recent_df = _fetch_windowed_reviews(window_days=WINDOW_DAYS, offset_days=0)
        baseline_df = _fetch_windowed_reviews(
            window_days=BASELINE_DAYS,
            offset_days=WINDOW_DAYS,
        )
    except (sqlite3.Error, pd.errors.DatabaseError):
        return _empty_alert_result()

    recent_negative_pct = _negative_pct(recent_df)
    baseline_negative_pct = _negative_pct(baseline_df)
    spike_delta = round(recent_negative_pct - baseline_negative_pct, 1)
    spike_detected = bool(spike_delta >= SPIKE_THRESHOLD)
    insufficient_data = bool(len(recent_df) < MIN_REVIEWS)

    negative_reviews = (
        recent_df[recent_df["sentiment"] < 0]["review"]
        .dropna()
        .astype(str)
        .tolist()
    )
    top_risk_keywords = _extract_risk_keywords(negative_reviews)
    risk_score, risk_level = _compute_risk_score(recent_negative_pct, spike_delta)

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "spike_detected": spike_detected,
        "recent_negative_pct": recent_negative_pct,
        "baseline_negative_pct": baseline_negative_pct,
        "spike_delta": float(spike_delta),
        "top_risk_keywords": top_risk_keywords,
        "recent_count": int(len(recent_df)),
        "baseline_count": int(len(baseline_df)),
        "insufficient_data": insufficient_data,
    }
