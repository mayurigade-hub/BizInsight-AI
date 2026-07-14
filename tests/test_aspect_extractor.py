from aspect_sentiment import analyze_aspect_sentiment


def test_negative_delivery():

    review = "The delivery was delayed."

    result = analyze_aspect_sentiment(review)

    assert result["Delivery"] == "Negative"


def test_positive_packaging():

    review = "Packaging was excellent."

    result = analyze_aspect_sentiment(review)

    assert result["Packaging"] == "Positive"


def test_negative_price():

    review = "The product is too expensive."

    result = analyze_aspect_sentiment(review)

    assert result["Price"] == "Negative"


def test_positive_quality():

    review = "The quality is amazing."

    result = analyze_aspect_sentiment(review)

    assert result["Product Quality"] == "Positive"


def test_positive_customer_service():

    review = "Customer support solved my issue."

    result = analyze_aspect_sentiment(review)

    assert result["Customer Service"] == "Positive"


def test_multiple_aspects_mixed_sentiment():

    review = (
        "Delivery was late but "
        "packaging was good."
    )

    result = analyze_aspect_sentiment(review)

    assert result["Delivery"] == "Negative"
    assert result["Packaging"] == "Positive"


def test_no_aspect_returns_empty_dict():

    review = "I bought this yesterday."

    assert analyze_aspect_sentiment(review) == {}