import React, { useState } from 'react';
import { useDashboard } from '../hooks/useDashboard';
import StockCard from '../components/cards/StockCard';
import StockChart from '../components/charts/StockChart';
import NewsFeed from '../components/panels/NewsFeed';
import MacroPanel from '../components/panels/MacroPanel';
import TrendingTable from '../components/panels/TrendingTable';
import { formatDistanceToNow } from 'date-fns';
import './Dashboard.css';

function LiveDot() {
  return <span className="live-dot" aria-label="live" />;
}

function Header({ lastUpdated, refreshing, onRefresh }) {
  return (
    <header className="dashboard-header">
      <div className="dh-left">
        <div className="dh-brand">
          <span className="dh-logo mono">SMSA</span>
          <div className="dh-title-block">
            <h1 className="dh-title">Stock Market Sentiment Analyzer</h1>
            <p className="dh-subtitle text-muted">FinBERT + Llama 3.2 · AAPL GOOGL META AMZN NFLX TSLA MSFT NVDA AMD ORCL</p>
          </div>
        </div>
      </div>
      <div className="dh-right">
        <div className="dh-status">
          <LiveDot />
          <span className="text-muted" style={{ fontSize: '0.72rem' }}>
            {lastUpdated
              ? `Updated ${formatDistanceToNow(lastUpdated, { addSuffix: true })}`
              : 'Loading…'}
          </span>
        </div>
        <button
          className={`refresh-btn ${refreshing ? 'refreshing' : ''}`}
          onClick={onRefresh}
          disabled={refreshing}
        >
          {refreshing ? '⟳ Refreshing…' : '⟳ Refresh Now'}
        </button>
      </div>
    </header>
  );
}

function SummaryBar({ stocks = [] }) {
  const bullish = stocks.filter(s => s.sentiment_label === 'bullish').length;
  const bearish = stocks.filter(s => s.sentiment_label === 'bearish').length;
  const neutral = stocks.filter(s => s.sentiment_label === 'neutral').length;
  const buySignals = stocks.filter(s => s.signal === 'Buy').length;
  const sellSignals = stocks.filter(s => s.signal === 'Sell').length;
  const holdSignals = stocks.length - buySignals - sellSignals;

  return (
    <div className="summary-bar">
      <div className="sb-item">
        <span className="sb-label text-muted">Stock Sentiment</span>
        <div className="sb-pills">
          <span className="sb-pill sb-pill--bullish">{bullish} Bullish</span>
          <span className="sb-pill sb-pill--neutral">{neutral} Neutral</span>
          <span className="sb-pill sb-pill--bearish">{bearish} Bearish</span>
        </div>
      </div>
      <div className="sb-divider" />
      <div className="sb-item">
        <span className="sb-label text-muted">Trade Signals</span>
        <div className="sb-pills">
          <span className="sb-pill sb-pill--buy">{buySignals} Buy</span>
          <span className="sb-pill sb-pill--sell">{sellSignals} Sell</span>
          <span className="sb-pill sb-pill--hold">{holdSignals} Hold</span>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { data, loading, error, refreshing, lastUpdated, manualRefresh } = useDashboard();
  const [selectedSymbol, setSelectedSymbol] = useState(null);

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loading-spinner" />
        <p className="text-muted">Fetching prices, running FinBERT + Llama 3.2…</p>
        <p className="text-muted" style={{ fontSize: '0.72rem', marginTop: 6 }}>
          First load may take 30–60 seconds while the model warms up.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error">
        <p className="text-bearish">⚠ {error}</p>
        <button className="refresh-btn" onClick={manualRefresh}>Retry</button>
      </div>
    );
  }

  const { stocks = [], trending = [], news_feed = [], macro_summary, macro_events = [] } = data || {};

  return (
    <div className="dashboard">
      <Header lastUpdated={lastUpdated} refreshing={refreshing} onRefresh={manualRefresh} />
      <SummaryBar stocks={stocks} />

      <main className="dashboard-body">
        <section className="section">
          <h2 className="section-title mono">All Stocks</h2>
          <div className="stocks-grid">
            {stocks.map(stock => (
              <StockCard
                key={stock.symbol}
                stock={stock}
                onClick={setSelectedSymbol}
              />
            ))}
          </div>
        </section>

        {selectedSymbol && (
          <section className="section">
            <div className="section-header-row">
              <h2 className="section-title mono">{selectedSymbol} — Detail View</h2>
              <button className="close-btn" onClick={() => setSelectedSymbol(null)}>✕ Close</button>
            </div>
            <StockChart symbol={selectedSymbol} />
          </section>
        )}

        <section className="section two-col">
          <TrendingTable trending={trending} onSelectStock={setSelectedSymbol} />
          <MacroPanel macroSummary={macro_summary} macroEvents={macro_events} />
        </section>

        <section className="section">
          <NewsFeed articles={news_feed} />
        </section>
      </main>

      <footer className="dashboard-footer">
        <span className="text-muted">Stock Market Sentiment Analyzer · Masters Portfolio Project · FinBERT + Llama 3.2 via Ollama</span>
      </footer>
    </div>
  );
}
