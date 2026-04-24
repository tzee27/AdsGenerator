import '../styles/RecommendationCard.css';

export default function RecommendationCard({ rec, selected, onSelect }) {
  return (
    <div
      className={`rec-card ${selected ? 'rec-card--selected' : ''}`}
      onClick={() => onSelect(rec.id)}
    >
      <div className="rec-card__header">
        <div className="rec-card__titles">
          <span className="rec-card__product-name">{rec.product}</span>
          <div className="rec-card__badges">
            <span className="rec-card__badge rec-card__badge--platform">{rec.platform}</span>
            <span className="rec-card__badge rec-card__badge--format">{rec.format}</span>
          </div>
        </div>
        <div className={`rec-card__select-indicator ${selected ? 'rec-card__select-indicator--active' : ''}`}>
          {selected && (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" width="14" height="14">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          )}
        </div>
      </div>

      <div className="rec-card__strategy-list">
        <div className="rec-card__strategy-item">
          <div className="rec-card__strategy-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
            </svg>
          </div>
          <div className="rec-card__strategy-content">
            <span className="rec-card__strategy-label">Target Audience</span>
            <p className="rec-card__strategy-val">{rec.audience}</p>
          </div>
        </div>

        <div className="rec-card__strategy-item">
          <div className="rec-card__strategy-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
              <line x1="12" y1="1" x2="12" y2="23"/>
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
          </div>
          <div className="rec-card__strategy-content">
            <span className="rec-card__strategy-label">Pricing Strategy</span>
            <p className="rec-card__strategy-val">{rec.pricing}</p>
          </div>
        </div>

        <div className="rec-card__strategy-item">
          <div className="rec-card__strategy-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div className="rec-card__strategy-content">
            <span className="rec-card__strategy-label">Optimal Timing</span>
            <p className="rec-card__strategy-val">{rec.bestTime}</p>
          </div>
        </div>
      </div>

      <div className="rec-card__insight">
        <div className="rec-card__insight-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
          <span>AI Strategy Insight</span>
        </div>
        <p>{rec.reason}</p>
      </div>

      <div className="rec-card__footer">
        <span className="rec-card__select-text">
          {selected ? 'Recommendation Selected' : 'Click to select this strategy'}
        </span>
      </div>
    </div>
  );
}
