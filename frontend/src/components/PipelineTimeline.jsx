import { useEffect, useState } from 'react';
import { PIPELINE_STEPS } from '../context/jobConstants';
import '../styles/PipelineTimeline.css';

/**
 * Vertical timeline of the 6 pipeline steps. Reads `currentStepIndex` and
 * `status` to colour each step; an extra blink keeps the active row alive.
 */
export default function PipelineTimeline({
  currentStepIndex,
  status,
  startedAt,
  campaignLabel,
  area,
  compact = false,
}) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (status !== 'running') return undefined;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [status]);

  const elapsedSeconds = startedAt ? Math.max(0, Math.floor((now - startedAt) / 1000)) : 0;
  const totalEstimated = PIPELINE_STEPS.reduce((sum, s) => sum + s.estimatedMs, 0);
  const progressPct = Math.min(
    100,
    Math.round(((startedAt ? now - startedAt : 0) / totalEstimated) * 100)
  );

  return (
    <div className={`timeline ${compact ? 'timeline--compact' : ''}`}>
      {!compact && (
        <div className="timeline__header">
          <div className="timeline__head-left">
            <span className="timeline__label">Active campaign</span>
            <h3 className="timeline__title">{campaignLabel || 'Inventory analysis'}</h3>
            <p className="timeline__sub">
              {area ? `Region: ${area}` : 'Region: backend default'}
              {' • '}
              {elapsedSeconds}s elapsed
            </p>
          </div>
          <div className="timeline__head-right">
            <div className="timeline__progress-ring" style={{ '--pct': progressPct }}>
              <svg viewBox="0 0 36 36">
                <path
                  className="timeline__progress-track"
                  d="M18 2.5 a 15.5 15.5 0 0 1 0 31 a 15.5 15.5 0 0 1 0 -31"
                />
                <path
                  className="timeline__progress-fill"
                  strokeDasharray={`${progressPct}, 100`}
                  d="M18 2.5 a 15.5 15.5 0 0 1 0 31 a 15.5 15.5 0 0 1 0 -31"
                />
              </svg>
              <span className="timeline__progress-text">{progressPct}%</span>
            </div>
          </div>
        </div>
      )}

      <ol className="timeline__steps">
        {PIPELINE_STEPS.map((step, idx) => {
          const state = stepState(idx, currentStepIndex, status);
          return (
            <li key={step.id} className={`timeline__step timeline__step--${state}`}>
              <div className="timeline__marker">
                {state === 'done' ? (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" width="14" height="14">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : state === 'active' ? (
                  <span className="timeline__pulse" />
                ) : (
                  <span className="timeline__dot" />
                )}
              </div>

              <div className="timeline__body">
                <div className="timeline__row">
                  <span className="timeline__step-label">{step.label}</span>
                  <span className={`timeline__phase-tag timeline__phase-tag--${step.phase.toLowerCase()}`}>
                    Phase {step.phase}
                  </span>
                </div>
                <p className="timeline__desc">{step.description}</p>

                {state === 'active' && (
                  <div className="timeline__active-meta">
                    <span className="timeline__active-dot" />
                    Working…
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      {!compact && status === 'running' && (
        <p className="timeline__hint">
          You can navigate around the app — this campaign keeps running in the background.
        </p>
      )}
    </div>
  );
}

function stepState(idx, currentStepIndex, status) {
  // After successful completion of phase B, every step is done.
  if (status === 'completed') return 'done';
  if (status === 'awaiting') {
    // Phase A finished; mark all phase-A steps done, phase-B steps pending.
    return PIPELINE_STEPS[idx].phase === 'A' ? 'done' : 'pending';
  }
  if (status === 'error') {
    if (idx < currentStepIndex) return 'done';
    if (idx === currentStepIndex) return 'failed';
    return 'pending';
  }
  // status === 'running' (or 'idle' which won't render this normally)
  if (idx < currentStepIndex) return 'done';
  if (idx === currentStepIndex) return 'active';
  return 'pending';
}
