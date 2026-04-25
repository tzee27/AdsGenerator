/**
 * Pipeline metadata shared between the JobContext provider and the UI
 * components that visualise it. Lives in its own module so React Fast Refresh
 * can keep the JSX-only files (JobContext.jsx, etc.) cleanly hot-swappable.
 */

export const PIPELINE_STEPS = [
  {
    id: 'risk',
    label: 'Risk Analysis',
    phase: 'A',
    estimatedMs: 800,
    description: 'Scoring inventory by expiry, exposure, and days unsold.',
  },
  {
    id: 'context',
    label: 'Live Context',
    phase: 'A',
    estimatedMs: 8000,
    description: "Searching today's events, trending formats, and ad costs.",
  },
  {
    id: 'strategy',
    label: 'Strategy Planning',
    phase: 'A',
    estimatedMs: 3500,
    description: 'Drafting three diverse ad strategies and matching products.',
  },
  {
    id: 'content',
    label: 'Content Generation',
    phase: 'B',
    estimatedMs: 6500,
    description: 'Composing three scroll-stopping ad copy variants.',
  },
  {
    id: 'image',
    label: 'Image Synthesis',
    phase: 'B',
    estimatedMs: 22000,
    description: 'Asking Gemini for a hero image based on the chosen strategy.',
  },
  {
    id: 'explanation',
    label: 'Explanation',
    phase: 'B',
    estimatedMs: 4500,
    description: 'Building the financial projection and risk vs reward verdict.',
  },
];

export const STEPS_BY_PHASE = {
  A: PIPELINE_STEPS.filter((s) => s.phase === 'A'),
  B: PIPELINE_STEPS.filter((s) => s.phase === 'B'),
};

export const FIRST_B_INDEX = PIPELINE_STEPS.findIndex((s) => s.phase === 'B');

/** Find the step index whose cumulative estimated time covers `elapsedMs`. */
export function stepIndexFromElapsed(phase, elapsedMs) {
  const steps = STEPS_BY_PHASE[phase];
  const offset = phase === 'A' ? 0 : FIRST_B_INDEX;
  let cumulative = 0;
  for (let i = 0; i < steps.length; i += 1) {
    cumulative += steps[i].estimatedMs;
    if (elapsedMs < cumulative) return offset + i;
  }
  // Past all estimated durations — pin to the last step until fetch returns.
  return offset + steps.length - 1;
}
