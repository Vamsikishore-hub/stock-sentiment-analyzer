import React, { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import './NewsFeed.css';

const SENTIMENT_ICON = { bullish: '▲', bearish: '▼', neutral: '◆' };

function NewsItem({ article }) {
  const {
    title, source, url, published_at,
    related_symbols, sentiment_label, is_reddit,
  } = article;

  const label = sentiment_label || 'neutral';
  const timeAgo = published_at
    ? formatDistanceToNow(new Date(published_at), { addSuffix: true })
    : 'unknown time';

  const symbols = related_symbols?.split(',').filter(Boolean) || [];

  return (
    <div className={`news-item news-item--${label}`}>
      <div className="ni-meta">
        <span className={`ni-sentiment ni-sentiment--${label}`}>
          {SENTIMENT_ICON[label]} {label}
        </span>
        {is_reddit && <span className="ni-reddit">Reddit</span>}
        <span className="ni-source text-muted">{source}</span>
        <span className="ni-time text-muted">{timeAgo}</span>
      </div>
      <a
        href={url || '#'}
        target="_blank"
        rel="noopener noreferrer"
        className="ni-title"
      >
        {title}
      </a>
      {symbols.length > 0 && (
        <div className="ni-symbols">
          {symbols.map(s => (
            <span key={s} className="ni-symbol-tag">{s}</span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function NewsFeed({ articles = [] }) {
  const [filter, setFilter] = useState('all');

  const filtered = filter === 'all'
    ? articles
    : articles.filter(a => a.sentiment_label === filter);

  return (
    <div className="news-feed">
      <div className="nf-header">
        <span className="nf-title mono">Live News Feed</span>
        <div className="nf-filters">
          {['all', 'bullish', 'neutral', 'bearish'].map(f => (
            <button
              key={f}
              className={`nf-filter ${filter === f ? 'active' : ''} ${f !== 'all' ? `nf-filter--${f}` : ''}`}
              onClick={() => setFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
      <div className="nf-list">
        {filtered.length === 0 ? (
          <p className="nf-empty text-muted">No articles match this filter.</p>
        ) : (
          filtered.map(a => <NewsItem key={a.id} article={a} />)
        )}
      </div>
    </div>
  );
}
