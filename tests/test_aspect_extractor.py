from aspect_sentiment import analyze_aspect_sentiment
import pandas as pd

from dashboard_aspects import (
    build_aspect_summary,
    get_aspect_sentiment_label,
    normalize_aspect_sentiment,
)


def test_get_label_plain_string():

    result = analyze_aspect_sentiment(review)

    assert result["Delivery"] == "Negative"


def test_positive_packaging():
    sentiment = {"Delivery": "Negative"}

    assert get_aspect_sentiment_label(sentiment, "Delivery") == "Negative"


def test_get_label_nested_dict():

    result = analyze_aspect_sentiment(review)

    assert result["Packaging"] == "Positive"
    sentiment = {
        "Delivery": {"sentiment": "Negative", "confidence": 0.91}
    }

    assert get_aspect_sentiment_label(sentiment, "Delivery") == "Negative"


def test_get_label_missing_aspect_defaults_neutral():

    result = analyze_aspect_sentiment(review)

    assert result["Price"] == "Negative"
    sentiment = {"Delivery": "Negative"}

    assert get_aspect_sentiment_label(sentiment, "Packaging") == "Neutral"


def test_normalize_aspect_sentiment_string_input():

    result = analyze_aspect_sentiment(review)

    assert result["Product Quality"] == "Positive"


def test_positive_customer_service():
    value = "{'Delivery': 'Negative'}"

    result = normalize_aspect_sentiment(value)

    assert result == {"Delivery": "Negative"}


    result = analyze_aspect_sentiment(review)

    assert result["Customer Service"] == "Positive"


def test_multiple_aspects_mixed_sentiment():
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

    result = analyze_aspect_sentiment(review)

    assert result["Delivery"] == "Negative"
    assert result["Packaging"] == "Positive"
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

def test_no_aspect_returns_empty_dict():
    summary = build_aspect_summary(df)

    delivery_row = summary[summary["Aspect"] == "Delivery"].iloc[0]

    assert analyze_aspect_sentiment(review) == {}
    assert delivery_row["Positive"] == 1
    assert delivery_row["Negative"] == 1
    assert delivery_row["Neutral"] == 0
