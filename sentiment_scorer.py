from dataclasses import dataclass

from nltk.sentiment.vader import SentimentIntensityAnalyzer
from transformers import pipeline


@dataclass
class SentimentResult:
    vader: float | None
    finbert: float | None


class SentimentScorer:
    """
    Compute sentiment scores using:
      - VADER (lexicon-based, fast)
      - FinBERT (finance-specific transformer)

    All scores normalized to [-1, 1].
    """

    def __init__(
        self,
        use_vader: bool = True,
        use_finbert: bool = True,
        finbert_model_name: str = "yiyanghkust/finbert-tone",
    ):
        self.use_vader = use_vader
        self.use_finbert = use_finbert

        # --- VADER ---
        self.vader_analyzer = SentimentIntensityAnalyzer() if use_vader else None

        # --- FinBERT ---
        if use_finbert:
            self.finbert_pipeline = pipeline(
                "text-classification",
                model=finbert_model_name,
                tokenizer=finbert_model_name,
                return_all_scores=True,
                truncation=True,
                max_length=512,
            )
        else:
            self.finbert_pipeline = None

    def score(self, text: str) -> SentimentResult:
        """Return sentiment scores for a given text using all enabled models."""
        if not text or not text.strip():
            return SentimentResult(vader=None, finbert=None)

        vader_score = self._score_vader(text) if self.use_vader else None
        finbert_score = self._score_finbert(text) if self.use_finbert else None

        return SentimentResult(vader=vader_score, finbert=finbert_score)

    def _score_vader(self, text: str) -> float:
        """
        VADER returns:
          {'neg': x, 'neu': y, 'pos': z, 'compound': c}
        Use 'compound' which is already in [-1, 1].
        """
        scores = self.vader_analyzer.polarity_scores(text)
        return float(scores["compound"])

    def _score_finbert(self, text: str) -> float:
        """
        FinBERT returns probabilities for labels like:
          'positive', 'negative', 'neutral'
        Map to [-1, 1] using score = P(pos) - P(neg).
        """
        outputs = self.finbert_pipeline(text)[0]  # list of dicts per label
        probs = {o["label"].lower(): float(o["score"]) for o in outputs}

        p_pos = probs.get("positive", 0.0)
        p_neg = probs.get("negative", 0.0)

        # Simple mapping: pos → +1, neg → -1, neutral = middle
        return p_pos - p_neg
