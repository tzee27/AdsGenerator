import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { PIPELINE_STEPS } from '../context/jobConstants';
import { useJob } from '../context/jobHooks';
import '../styles/JobIndicator.css';

const TOTAL_ESTIMATED_MS = PIPELINE_STEPS.reduce((sum, s) => sum + s.estimatedMs, 0);

/**
 * Floating bottom-right widget that surfaces the active campaign on every page.
 * Hidden when status is idle. Clicking it routes to /generate.
 */
export default function JobIndicator() {
  const job = useJob();
  const navigate = useNavigate();
  const location = useLocation();
  const [now, setNow] = useState(() => Date.now());

  // Keep the progress bar moving while a phase is in flight.
  useEffect(() => {
    if (job.status !== 'running') return undefined;
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, [job.status]);

  if (job.status === 'idle') return null;
  // Don't show the floating widget when the user is already on /generate —
  // the in-page timeline already gives them all the info.
  if (location.pathname === '/generate' && job.status !== 'completed') return null;

  const elapsed = job.startedAt ? now - job.startedAt : 0;
  const progressPct = job.status === 'completed'
    ? 100
    : Math.min(98, Math.round((elapsed / TOTAL_ESTIMATED_MS) * 100));

  const activeStep = PIPELINE_STEPS[job.currentStepIndex] || PIPELINE_STEPS[0];

  const variantClass =
    job.status === 'error'
      ? 'job-indicator--error'
      : job.status === 'completed'
        ? 'job-indicator--success'
        : job.status === 'awaiting'
          ? 'job-indicator--awaiting'
          : 'job-indicator--running';

  const onOpen = () => {
    job.actions.dismissNotification();
    navigate('/generate');
  };

  return (
    <button type="button" className={`job-indicator ${variantClass}`} onClick={onOpen}>
      <div className="job-indicator__icon">
        {job.status === 'running' && <span className="job-indicator__spinner" />}
        {job.status === 'awaiting' && (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="18" height="18">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        )}
        {job.status === 'completed' && (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" width="18" height="18">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        )}
        {job.status === 'error' && (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="18" height="18">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        )}
      </div>

      <div className="job-indicator__body">
        <div className="job-indicator__head">
          <span className="job-indicator__campaign">{job.campaignLabel || 'Campaign'}</span>
          <span className="job-indicator__status">{statusLabel(job.status)}</span>
        </div>

        <p className="job-indicator__step">
          {job.status === 'running' && `Step ${job.currentStepIndex + 1}/${PIPELINE_STEPS.length}: ${activeStep.label}`}
          {job.status === 'awaiting' && 'Pick a strategy to continue'}
          {job.status === 'completed' && 'Tap to view results'}
          {job.status === 'error' && (job.error?.message || 'Something went wrong — tap to inspect')}
        </p>

        {(job.status === 'running' || job.status === 'awaiting') && (
          <div className="job-indicator__bar">
            <div className="job-indicator__bar-fill" style={{ width: `${progressPct}%` }} />
          </div>
        )}
      </div>

      <span className="job-indicator__chevron" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="14" height="14">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </span>
    </button>
  );
}

function statusLabel(status) {
  switch (status) {
    case 'running': return 'Running';
    case 'awaiting': return 'Action needed';
    case 'completed': return 'Done';
    case 'error': return 'Failed';
    default: return '';
  }
}
