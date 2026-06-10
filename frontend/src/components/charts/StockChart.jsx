import React, { useState, useEffect } from 'react';
import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts';
import { fetchStockDetail } from '../../services/api';
import { format } from 'date-fns';
import './StockChart.css';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>
          {p.name === 'Price' ? `$${Number(p.value).toFixed(2)}` : `${Number(p.value).toFixed(3)}`}
          {' '}{p.name}
        </p>
      ))}
    </div>
  );
};

export default function StockChart({ symbol }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    fetchStockDetail(symbol)
      .then(d => { setDetail(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [symbol]);

  if (loading) {
    return (
      <div className="stock-chart-shell">
        <div className="skeleton" style={{ height: 280, borderRadius: 8 }} />
      </div>
    );
  }

  // Build chart data — use sentiment history even if no prices yet
  const history = detail?.price_history || [];
  const hasPrice = history.some(p => p.price > 0);
  const hasSentiment = history.some(p => p.sentiment_score !== 0);

  // If no price history at all, fall back to sentiment-only from the current stock
  const chartData = history.length > 0
    ? history.map(p => ({
        time: format(new Date(p.time), 'HH:mm'),
        ...(hasPrice ? { Price: p.price } : {}),
        Sentiment: p.sentiment_score,
      }))
    : [];

  if (chartData.length === 0) {
    return (
      <div className="stock-chart-shell empty">
        <div style={{ textAlign: 'center' }}>
          <p className="text-muted" style={{ marginBottom: 8 }}>
            No historical data yet — data accumulates over time.
          </p>
          <p className="text-muted" style={{ fontSize: '0.7rem' }}>
            The chart will populate after the next analysis cycle (~15 min).
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="stock-chart-shell">
      <div className="chart-header">
        <span className="chart-title mono">
          {symbol} — {hasPrice ? 'Price & Sentiment' : 'Sentiment'} Trend
        </span>
        <span className="chart-subtitle text-muted">{chartData.length} data points</span>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis
            dataKey="time"
            tick={{ fill: 'var(--text-muted)', fontSize: 11, fontFamily: 'IBM Plex Mono' }}
            axisLine={{ stroke: 'var(--border)' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          {hasPrice && (
            <YAxis
              yAxisId="price"
              orientation="left"
              tick={{ fill: 'var(--text-muted)', fontSize: 11, fontFamily: 'IBM Plex Mono' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={v => `$${v}`}
            />
          )}
          <YAxis
            yAxisId="sentiment"
            orientation={hasPrice ? "right" : "left"}
            domain={[-1, 1]}
            tick={{ fill: 'var(--text-muted)', fontSize: 11, fontFamily: 'IBM Plex Mono' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 11, fontFamily: 'IBM Plex Mono', color: 'var(--text-secondary)' }}
          />
          <ReferenceLine yAxisId="sentiment" y={0} stroke="var(--border-bright)" strokeDasharray="4 4" />
          <Bar
            yAxisId="sentiment"
            dataKey="Sentiment"
            fill="var(--accent-cyan)"
            opacity={0.4}
            radius={[2, 2, 0, 0]}
          />
          {hasPrice && (
            <Line
              yAxisId="price"
              type="monotone"
              dataKey="Price"
              stroke="var(--accent-cyan)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: 'var(--accent-cyan)' }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
