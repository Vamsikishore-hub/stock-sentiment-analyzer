import React from 'react';
import './StockCard.css';

const SIGNAL_COLOR = { Buy: 'buy', Sell: 'sell', Hold: 'hold' };
const SENTIMENT_LABEL = { bullish: 'Bullish', bearish: 'Bearish', neutral: 'Neutral' };

function SentimentBar({ score }) {
  // score: -1 to +1
  const pct = ((score + 1) / 2) * 100;
  const color = score >= 0.15 ? 'var(--bullish)' : score <= -0.15 ? 'var(--bearish)' : 'var(--neutral)';
  return (
    <div className="sentiment-bar-track">
      <div className="sentiment-bar-center" />
      <div
        className="sentiment-bar-fill"
        style={{
          left: score >= 0 ? '50%' : `${pct}%`,
          width: `${Math.abs(score) * 50}%`,
          background: color,
        }}
      />
    </div>
  );
}

export default function StockCard({ stock, onClick }) {
  const {
    symbol, price, change, change_pct,
    sentiment_label, sentiment_score, signal, gpt_reasoning, mention_count,
  } = stock;

  const isUp = change >= 0;
  const sentClass = sentiment_label || 'neutral';

  return (
    <div className={`stock-card stock-card--${sentClass}`} onClick={() => onClick?.(symbol)}>
      {/* Header */}
      <div className="sc-header">
        <div className="sc-symbol">{symbol}</div>
        <span className={`sc-signal sc-signal--${SIGNAL_COLOR[signal] || 'hold'}`}>
          {signal}
        </span>
      </div>

      {/* Price */}
      <div className="sc-price-row">
        <span className="sc-price mono">${price?.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
        <span className={`sc-change mono ${isUp ? 'text-bullish' : 'text-bearish'}`}>
          {isUp ? '▲' : '▼'} {Math.abs(change_pct).toFixed(2)}%
        </span>
      </div>

      {/* Sentiment badge + bar */}
      <div className="sc-sentiment-row">
        <span className={`sc-badge sc-badge--${sentClass}`}>
          {SENTIMENT_LABEL[sentClass]}
        </span>
        <span className="sc-score mono text-muted">{sentiment_score > 0 ? '+' : ''}{sentiment_score?.toFixed(3)}</span>
      </div>

      <SentimentBar score={sentiment_score || 0} />

      {/* GPT reasoning */}
      {gpt_reasoning && (
        <p className="sc-reasoning">{gpt_reasoning}</p>
      )}

      {/* Footer */}
      <div className="sc-footer">
        <span className="sc-mentions text-muted">{mention_count} mentions</span>
        <span className="sc-hint text-muted">click for detail →</span>
      </div>
    </div>
  );
}
