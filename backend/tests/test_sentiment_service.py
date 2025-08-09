from app.services.sentiment_service import SentimentService


def test_basic_sentiment():
    svc = SentimentService()
    pos = svc.analyze_text("I love this product, it's fantastic!")
    neg = svc.analyze_text("This is terrible and disappointing.")
    assert pos.compound > 0.2
    assert neg.compound < -0.2