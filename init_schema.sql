USE sentiment_news;

CREATE TABLE IF NOT EXISTS articles (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  url TEXT,
  url_hash CHAR(64) NOT NULL UNIQUE,
  headline TEXT NOT NULL,
  source VARCHAR(128) NULL,
  published_dt DATETIME(6) NULL,   -- store UTC
  scraped_html MEDIUMTEXT NULL,
  full_text MEDIUMTEXT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_pubdt (published_dt)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS tickers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  symbol VARCHAR(10) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS article_tickers (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  article_id BIGINT NOT NULL,
  ticker_id INT NOT NULL,
  mentions INT DEFAULT 0,
  pos_kw INT DEFAULT 0,
  neg_kw INT DEFAULT 0,
  tokens MEDIUMTEXT NULL,
  sentiment_dynamic DOUBLE NULL,
  sentiment_ml DOUBLE NULL,
  sentiment_keyword DOUBLE NULL,
  sentiment_combined DOUBLE NULL,
  headline_sentiment DOUBLE NULL,
  market_session VARCHAR(20) NULL,
  news_age_minutes DOUBLE NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_article_ticker (article_id, ticker_id),
  FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
  FOREIGN KEY (ticker_id)  REFERENCES tickers(id)  ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS predictions (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  article_ticker_id BIGINT NOT NULL,
  horizon ENUM('1hr','4hr','eod') NOT NULL,
  gk_prob DOUBLE NULL,
  predicted_pct DOUBLE NULL,
  prediction_time DATETIME(6) NOT NULL,   -- UTC
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_pred (article_ticker_id, horizon, prediction_time),
  FOREIGN KEY (article_ticker_id) REFERENCES article_tickers(id) ON DELETE CASCADE,
  INDEX idx_horizon (horizon),
  INDEX idx_predtime (prediction_time)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS actuals (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  article_ticker_id BIGINT NOT NULL,
  horizon ENUM('1hr','4hr','eod') NOT NULL,
  actual_pct DOUBLE NOT NULL,
  computed_at DATETIME(6) NOT NULL,       -- UTC
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_actual (article_ticker_id, horizon, computed_at),
  FOREIGN KEY (article_ticker_id) REFERENCES article_tickers(id) ON DELETE CASCADE
) ENGINE=InnoDB;
