import React from 'react';
import './MacroPanel.css';

const IMPACT_ICON = { positive: '▲', negative: '▼', neutral: '◆' };

export default function MacroPanel({ macroSummary, macroEvents = [] }) {
  return (
    <div className="macro-panel">
      <div className="mp-header">
        <span className="mp-title mono">Llama 3.2 Macro Analysis</span>
        <span className="mp-badge">AI</span>
      </div>

      {macroSummary ? (
        <div className="mp-summary">
          <p className="mp-summary-text">{macroSummary}</p>
        </div>
      ) : (
        <div className="mp-empty text-muted">
          Llama 3.2 analysis runs every {process.env.REACT_APP_REFRESH_MINUTES || 15} minutes.
        </div>
      )}

      {macroEvents.length > 0 && (
        <div className="mp-events">
          {macroEvents.map((evt, i) => {
            const impact = evt.impact || 'neutral';
            const symbols = evt.affected_symbols?.split(',').filter(Boolean) || [];
            return (
              <div key={i} className={`mp-event mp-event--${impact}`}>
                <div className="mpe-header">
                  <span className={`mpe-impact mpe-impact--${impact}`}>
                    {IMPACT_ICON[impact]} {impact}
                  </span>
                  {evt.event_type && (
                    <span className="mpe-type text-muted">{evt.event_type}</span>
                  )}
                </div>
                <p className="mpe-summary">{evt.summary}</p>
                {symbols.length > 0 && (
                  <div className="mpe-symbols">
                    {symbols.map(s => (
                      <span key={s} className="mpe-symbol">{s}</span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
