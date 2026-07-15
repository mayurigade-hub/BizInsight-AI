from aspect_sentiment import analyze_aspect_sentiment


def calculate_confidence(result):

    confidence = {}

    for aspect, sentiment in result.items():

        if sentiment == "Positive":
            confidence[aspect] = {
                "sentiment": sentiment,
                "confidence": 0.93
            }

        elif sentiment == "Negative":
            confidence[aspect] = {
                "sentiment": sentiment,
                "confidence": 0.91
            }

        else:

            confidence[aspect] = {
                "sentiment": sentiment,
                "confidence": 0.72
            }

    return confidence


def analyze_review_ai(review):

    result = analyze_aspect_sentiment(review)

    return calculate_confidence(result)