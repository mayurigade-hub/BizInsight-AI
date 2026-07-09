from aspect_sentiment import analyze_aspect_sentiment
from ai_aspect_engine import analyze_review_ai


class AspectModel:

    def __init__(self):

        self.engine = "Rule-Based"

    def set_engine(self, engine):

        self.engine = engine

    def analyze(self, review):

        if self.engine == "AI":

            return analyze_review_ai(review)

        return analyze_aspect_sentiment(review)


aspect_model = AspectModel()