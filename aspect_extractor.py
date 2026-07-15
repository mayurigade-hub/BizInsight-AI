"""
Aspect Extraction Module for BizInsight AI

This module identifies business-related aspects mentioned
in customer reviews using rule-based keyword matching.
"""

import re

ASPECT_KEYWORDS = {
    "Product Quality": [
        "quality",
        "durable",
        "defective",
        "broken",
        "damage",
        "material",
        "performance",
        "poor quality",
        "excellent quality",
        "good quality"
    ],

    "Price": [
        "price",
        "cost",
        "expensive",
        "cheap",
        "value",
        "worth",
        "pricing",
        "affordable"
    ],

    "Delivery": [
        "delivery",
        "shipping",
        "shipment",
        "courier",
        "late",
        "delay",
        "arrived",
        "dispatch",
        "delivered"
    ],

    "Packaging": [
        "packaging",
        "package",
        "box",
        "packed",
        "seal",
        "wrapped",
        "wrapper"
    ],

    "Customer Service": [
        "service",
        "support",
        "staff",
        "customer care",
        "representative",
        "agent",
        "helpdesk",
        "response"
    ]
}

# Precompile word-boundary patterns once at import time so we don't
# recompile regex objects on every extract_aspects() call.
_KEYWORD_PATTERNS = {
    aspect: [
        (keyword, re.compile(r"\b" + re.escape(keyword) + r"\b"))
        for keyword in keywords
    ]
    for aspect, keywords in ASPECT_KEYWORDS.items()
}


def clean_text(text: str) -> str:
    """
    Clean review text for keyword matching.

    Args:
        text (str): Customer review.

    Returns:
        str: Cleaned lowercase text.
    """

    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_aspects(review: str):
    """
    Detect aspects mentioned in a review.

    Uses word-boundary regex matching instead of plain substring
    search, so keywords only match whole words (or whole phrases,
    for multi-word keywords like "customer care"), not fragments
    inside unrelated longer words (e.g. "cost" no longer matches
    inside "accosted").

    Args:
        review (str)

    Returns:
        list[str]
    """

    review = clean_text(review)

    detected = []

    for aspect, patterns in _KEYWORD_PATTERNS.items():

        for keyword, pattern in patterns:

            if pattern.search(review):
                detected.append(aspect)
                break

    return detected


def extract_aspects_bulk(reviews):
    """
    Detect aspects for multiple reviews.

    Args:
        reviews (list[str])

    Returns:
        list[list[str]]
    """

    return [extract_aspects(review) for review in reviews]