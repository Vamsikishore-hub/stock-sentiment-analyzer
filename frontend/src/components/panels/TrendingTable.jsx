import React from 'react';
import './TrendingTable.css';

const SIGNAL_COLOR = { Buy: 'buy', Sell: 'sell', Hold: 'hold' };

export default function TrendingTable({ trending = [], onSelectStock }) {
  return (
    <div className="trending-table">
      <div className="tt-header">
        <span className="tt-title mono">Trending Today</span>
        <span className="tt-sub text-muted">by mention volume</span>
      </div>
      <table className="tt-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Symbol</th>
            <th>Sentiment</th>
            <th>Score</th>
            <th>Signal</th>
            <th>Mentions</th>
          </tr>
        </thead>
        <tbody>
          {trending.map((s, i) => {
            const label = s.sentiment_label || 'neutral';
            const signal = s.signal || 'Hold';
            return (
              <tr
                key={s.symbol}
                className="tt-row"
                onClick={() => onSelectStock?.(s.symbol)}
              >
                <td className="tt-rank text-muted mono">{i + 1}</td>
                <td className="tt-symbol mono">{s.symbol}</td>
                <td>
                  <span className={`tt-badge tt-badge--${label}`}>{label}</span>
                </td>
                <td className={`mono tt-score ${label === 'bullish' ? 'text-bullish' : label === 'bearish' ? 'text-bearish' : 'text-neutral'}`}>
                  {s.sentiment_score >= 0 ? '+' : ''}{s.sentiment_score?.toFixed(3)}
                </td>
                <td>
                  <span className={`tt-signal tt-signal--${SIGNAL_COLOR[signal] || 'hold'}`}>{signal}</span>
                </td>
                <td className="tt-mentions text-muted mono">{s.mention_count}</td>
              </tr>
            );
          })}
          {trending.length === 0 && (
            <tr><td colSpan={6} className="tt-empty text-muted">No data yet</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
