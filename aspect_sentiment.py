from nltk.sentiment.vader import SentimentIntensityAnalyzer

from aspect_extractor import (
    extract_aspects,
    ASPECT_KEYWORDS
)

# Initialize VADER
sia = SentimentIntensityAnalyzer()

# Thresholds
POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05

# Split review into clauses
SEPARATORS = [
    ".",
    ",",
    ";",
    " but ",
    " however ",
    " although ",
    " though ",
]


def split_into_clauses(review: str) -> list[str]:
    """
    Split a review into smaller clauses while preserving
    connected positive phrases.
    """

    clauses = [review]

    for sep in SEPARATORS:

        new_clauses = []

        for clause in clauses:
            new_clauses.extend(clause.split(sep))

        clauses = new_clauses

    return [
        clause.strip()
        for clause in clauses
        if clause.strip()
    ]


def get_clause_sentiment(text: str) -> str:
    """
    Return Positive, Negative or Neutral
    using VADER.
    """

    score = sia.polarity_scores(text)["compound"]

    if score >= POSITIVE_THRESHOLD:
        return "Positive"

    if score <= NEGATIVE_THRESHOLD:
        return "Negative"

    return "Neutral"


def analyze_aspect_sentiment(review: str) -> dict[str, str]:
    """
    Analyze sentiment for every detected aspect.
    """

    aspects = extract_aspects(review)

    if not aspects:
        return {}

    clauses = split_into_clauses(review)

    results = {}

    for aspect in aspects:

        keywords = ASPECT_KEYWORDS.get(aspect, [])

        sentiment = "Neutral"

        for clause in clauses:

            clause_lower = clause.lower()

            # Check if any keyword of this aspect exists
            if any(keyword.lower() in clause_lower for keyword in keywords):

                sentiment = get_clause_sentiment(clause)

                break

        results[aspect] = sentiment

    return results