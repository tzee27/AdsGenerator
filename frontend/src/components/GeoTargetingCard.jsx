import { useEffect, useMemo, useState } from "react";
import "../styles/GeoTargetingCard.css";

const LOADING_STEPS = [
  "Searching area demographics...",
  "Finding who buys this product...",
  "Checking platform performance...",
];

function confidenceBarClass(score) {
  if (score >= 75) return "geo-card__confidence-fill--high";
  if (score >= 50) return "geo-card__confidence-fill--medium";
  return "geo-card__confidence-fill--low";
}

function normalizeConfidence(value) {
  const text = typeof value === "string" ? value : String(value || "LOW");
  const normalized = text.trim().toUpperCase();
  if (normalized === "HIGH" || normalized === "MEDIUM" || normalized === "LOW") {
    return normalized;
  }
  return "LOW";
}

function normalizeZone(zone) {
  if (typeof zone === "string") {
    const area = zone.trim();
    if (!area) return null;
    return { area, reason: "Matched from live search trends.", confidence: 60 };
  }
  if (zone && typeof zone === "object") {
    const area = String(zone.area || zone.zone || zone.name || "").trim();
    if (!area) return null;
    const reason = String(
      zone.reason || zone.why || zone.rationale || "Matched from live search trends.",
    ).trim();
    const raw = Number(zone.confidence ?? zone.score ?? 60);
    const confidence = Number.isFinite(raw) ? Math.max(0, Math.min(100, raw)) : 60;
    return { area, reason, confidence };
  }
  return null;
}

export default function GeoTargetingCard({
  productName,
  storeLocation,
  recommendation,
  isLoading,
  onRetry,
}) {
  const [visibleStep, setVisibleStep] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    if (!isLoading) {
      setVisibleStep(LOADING_STEPS.length);
      return undefined;
    }

    setVisibleStep(0);
    const intervalId = setInterval(() => {
      setVisibleStep((prev) => {
        if (prev >= LOADING_STEPS.length) {
          clearInterval(intervalId);
          return prev;
        }
        return prev + 1;
      });
    }, 1500);

    return () => clearInterval(intervalId);
  }, [isLoading]);

  const todayLabel = useMemo(
    () =>
      new Date().toLocaleDateString("en-MY", {
        day: "numeric",
        month: "short",
        year: "numeric",
      }),
    [],
  );

  if (isLoading) {
    return (
      <section className="geo-card geo-card--loading">
        <h3 className="geo-card__title">🔍 Researching local demand for {productName}...</h3>
        <div className="geo-card__loading-steps">
          {LOADING_STEPS.map((step, index) => (
            <p
              key={step}
              className={`geo-card__loading-step ${index < visibleStep ? "geo-card__loading-step--active" : ""}`}
            >
              ⏳ {step}
            </p>
          ))}
        </div>
        <div className="geo-card__skeleton" aria-hidden="true">
          <div className="geo-card__skeleton-line geo-card__skeleton-line--short" />
          <div className="geo-card__skeleton-line" />
          <div className="geo-card__skeleton-block" />
        </div>
      </section>
    );
  }

  const result = recommendation?.data || {};
  const source = recommendation?.source || "unknown";
  const confidence = normalizeConfidence(result.overallConfidence);
  const targetZones = (Array.isArray(result.targetZones) ? result.targetZones : [])
    .map(normalizeZone)
    .filter(Boolean);
  const avoidZones = (Array.isArray(result.avoidZones) ? result.avoidZones : [])
    .map(normalizeZone)
    .filter(Boolean);
  const demographic = result.targetDemographic || {};

  return (
    <section className="geo-card">
      <div className="geo-card__header">
        <div>
          <h3 className="geo-card__title">📍 Geo Targeting — {productName}</h3>
          <p className="geo-card__meta">Based on live web search • {todayLabel}</p>
        </div>
        <span className={`geo-card__confidence geo-card__confidence--${confidence.toLowerCase()}`}>
          {confidence}
        </span>
      </div>

      {source === "fallback_defaults" && (
        <div className="geo-card__warning">
          <span>⚠️ Using default targeting - web search unavailable. Retry for better results.</span>
          <button
            type="button"
            onClick={() => onRetry?.()}
            className="geo-card__warning-btn"
          >
            Retry
          </button>
        </div>
      )}

      <div className="geo-card__grid">
        <div>
          <h4 className="geo-card__section-title geo-card__section-title--target">✅ Target These Areas</h4>
          <div className="geo-card__zone-list">
            {targetZones.map((zone) => {
              const confidenceScore = Number(zone?.confidence || 0);
              return (
                <article key={`${zone?.area}-${zone?.reason}`} className="geo-card__zone-item">
                  <p className="geo-card__zone-area">{zone?.area || "Unknown area"}</p>
                  <div className="geo-card__confidence-track">
                    <div
                      className={`geo-card__confidence-fill ${confidenceBarClass(confidenceScore)}`}
                      style={{ width: `${Math.max(0, Math.min(confidenceScore, 100))}%` }}
                    />
                  </div>
                  <p className="geo-card__zone-reason">{zone?.reason || "No reason provided."}</p>
                </article>
              );
            })}
            {targetZones.length === 0 && (
              <p className="geo-card__empty">
                No clear target zones found yet.
              </p>
            )}
          </div>
        </div>

        <div>
          <h4 className="geo-card__section-title geo-card__section-title--avoid">❌ Avoid These Areas</h4>
          <div className="geo-card__zone-list">
            {avoidZones.map((zone) => (
              <article key={`${zone?.area}-${zone?.reason}`} className="geo-card__zone-item">
                <p className="geo-card__zone-area geo-card__zone-area--muted">{zone?.area || "Unknown area"}</p>
                <p className="geo-card__zone-reason">{zone?.reason || "No reason provided."}</p>
              </article>
            ))}
            {avoidZones.length === 0 && (
              <p className="geo-card__empty">
                No specific areas to avoid detected.
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="geo-card__pills">
        <span className="geo-card__pill">📍 {result.recommendedRadiusKm || 0}km radius</span>
        <span className="geo-card__pill">
          👥 {demographic.ageRange || "N/A"} {demographic.gender || "All"}
        </span>
        <span className="geo-card__pill">📱 {result.bestPlatform || "N/A"}</span>
        <span className="geo-card__pill">⏰ {result.bestTiming || "N/A"}</span>
      </div>

      <div className="geo-card__language">
        🗣️ Recommended ad language: {result.adLanguage || "N/A"}
      </div>

      <div className="geo-card__expand">
        <button
          type="button"
          onClick={() => setIsExpanded((prev) => !prev)}
          className="geo-card__expand-trigger"
        >
          <span>What did we find online?</span>
          <span className="geo-card__expand-icon">{isExpanded ? "-" : "+"}</span>
        </button>
        {isExpanded && (
          <div className="geo-card__expand-body">
            <p>{result.searchSummary || "No search summary available."}</p>
            <p>{result.reasoning || "No reasoning provided."}</p>
            <p className="geo-card__source">Source: {source}</p>
            <p className="geo-card__source">Store location: {storeLocation}</p>
          </div>
        )}
      </div>

    </section>
  );
}
