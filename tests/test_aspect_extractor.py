import pandas as pd

from dashboard_aspects import (
    build_aspect_summary,
    get_aspect_sentiment_label,
    normalize_aspect_sentiment,
)


def test_get_label_plain_string():

    sentiment = {"Delivery": "Negative"}

    assert get_aspect_sentiment_label(sentiment, "Delivery") == "Negative"


def test_get_label_nested_dict():

    sentiment = {
        "Delivery": {"sentiment": "Negative", "confidence": 0.91}
    }

    assert get_aspect_sentiment_label(sentiment, "Delivery") == "Negative"


def test_get_label_missing_aspect_defaults_neutral():

    sentiment = {"Delivery": "Negative"}

    assert get_aspect_sentiment_label(sentiment, "Packaging") == "Neutral"


def test_normalize_aspect_sentiment_string_input():

    value = "{'Delivery': 'Negative'}"

    result = normalize_aspect_sentiment(value)

    assert result == {"Delivery": "Negative"}


def test_build_aspect_summary_with_plain_string_values():

    df = pd.DataFrame(
        {
            "aspect_sentiment": [
                {"Delivery": "Negative"},
                {"Delivery": "Positive"},
            ]
        }
    )

    summary = build_aspect_summary(df)

    delivery_row = summary[summary["Aspect"] == "Delivery"].iloc[0]

    assert delivery_row["Negative"] == 1
    assert delivery_row["Positive"] == 1
    assert delivery_row["Neutral"] == 0


def test_build_aspect_summary_with_nested_ai_mode_values():

    df = pd.DataFrame(
        {
            "aspect_sentiment": [
                {
                    "Delivery": {
                        "sentiment": "Negative",
                        "confidence": 0.91,
                    },
                    "Customer Service": {
                        "sentiment": "Negative",
                        "confidence": 0.80,
                    },
                }
            ]
        }
    )

    summary = build_aspect_summary(df)

    delivery_row = summary[summary["Aspect"] == "Delivery"].iloc[0]
    service_row = summary[summary["Aspect"] == "Customer Service"].iloc[0]

    assert delivery_row["Negative"] == 1
    assert delivery_row["Neutral"] == 0

    assert service_row["Negative"] == 1
    assert service_row["Neutral"] == 0


def test_build_aspect_summary_with_mixed_plain_and_nested_values():

    df = pd.DataFrame(
        {
            "aspect_sentiment": [
                {"Delivery": "Positive"},
                {"Delivery": {"sentiment": "Negative", "confidence": 0.7}},
            ]
        }
    )

    summary = build_aspect_summary(df)

    delivery_row = summary[summary["Aspect"] == "Delivery"].iloc[0]

    assert delivery_row["Positive"] == 1
    assert delivery_row["Negative"] == 1
    assert delivery_row["Neutral"] == 0