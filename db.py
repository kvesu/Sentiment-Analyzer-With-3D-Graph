import hashlib
from datetime import datetime
from typing import Dict, Any, Iterable
from sqlalchemy import text
from config_db import get_mysql_engine

engine = get_mysql_engine()

def _sha256(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

def upsert_article(url: str,
                   headline: str,
                   source: str | None,
                   published_dt_utc: datetime | None,
                   scraped_html: str | None,
                   full_text: str | None) -> int:
    """
    Insert or update an article row, return its ID.
    De-duplicates by url_hash so the same URL isn't stored twice.
    """
    url_hash = _sha256(url)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO articles (url, url_hash, headline, source, published_dt, scraped_html, full_text)
            VALUES (:url, :url_hash, :headline, :source, :published_dt, :scraped_html, :full_text)
            ON DUPLICATE KEY UPDATE
              headline = VALUES(headline),
              source = COALESCE(VALUES(source), source),
              published_dt = COALESCE(VALUES(published_dt), published_dt),
              scraped_html = COALESCE(VALUES(scraped_html), scraped_html),
              full_text = COALESCE(VALUES(full_text), full_text)
        """), dict(
            url=url,
            url_hash=url_hash,
            headline=headline[:65535],
            source=source,
            published_dt=published_dt_utc,
            scraped_html=scraped_html,
            full_text=full_text,
        ))
        row = conn.execute(
            text("SELECT id FROM articles WHERE url_hash = :h"),
            {"h": url_hash}
        ).fetchone()
        return int(row[0])

def get_or_create_ticker(symbol: str) -> int:
    """Ensure ticker exists in DB and return its ID."""
    sym = (symbol or "").upper()[:10]
    with engine.begin() as conn:
        conn.execute(
            text("INSERT IGNORE INTO tickers (symbol) VALUES (:s)"),
            {"s": sym}
        )
        row = conn.execute(
            text("SELECT id FROM tickers WHERE symbol = :s"),
            {"s": sym}
        ).fetchone()
        return int(row[0])

def upsert_article_ticker(article_id: int,
                          ticker_id: int,
                          fields: Dict[str, Any]) -> int:
    """
    Insert or update row in article_tickers for (article, ticker) pair.
    Returns article_tickers.id.
    """
    if not fields:
        fields = {}

    # Build dynamic update clause
    update_clause = ", ".join([f"{k} = VALUES({k})" for k in fields.keys()])
    params = dict(article_id=article_id, ticker_id=ticker_id, **fields)

    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO article_tickers (article_id, ticker_id, {", ".join(fields.keys())})
            VALUES (:article_id, :ticker_id, {", ".join(":"+k for k in fields.keys())})
            ON DUPLICATE KEY UPDATE {update_clause}
        """), params)

        row = conn.execute(text("""
            SELECT id FROM article_tickers
            WHERE article_id = :a AND ticker_id = :t
        """), {"a": article_id, "t": ticker_id}).fetchone()
        return int(row[0])

def insert_prediction(article_ticker_id: int,
                      horizon: str,
                      gk_prob: float | None,
                      predicted_pct: float | None,
                      prediction_time_utc: datetime) -> None:
    """
    Insert a prediction row (ignore duplicates for same article_ticker_id+horizon+time).
    """
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT IGNORE INTO predictions
              (article_ticker_id, horizon, gk_prob, predicted_pct, prediction_time)
            VALUES (:at, :hz, :gk, :pp, :pt)
        """), {
            "at": article_ticker_id,
            "hz": horizon,
            "gk": gk_prob,
            "pp": predicted_pct,
            "pt": prediction_time_utc,
        })

def bulk_insert_actuals(rows: Iterable[Dict[str, Any]]) -> None:
    """
    Bulk insert actual returns into the actuals table.
    rows: iterable of dicts with keys:
      article_ticker_id, horizon, actual_pct, computed_at
    """
    rows = list(rows)
    if not rows:
        return
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT IGNORE INTO actuals
              (article_ticker_id, horizon, actual_pct, computed_at)
            VALUES (:article_ticker_id, :horizon, :actual_pct, :computed_at)
        """), rows)
