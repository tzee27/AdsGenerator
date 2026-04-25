/**
 * Global pipeline-job state.
 *
 * Lives at the App root so the user can navigate anywhere while the GLM /
 * Gemini calls run in the background. Surfaces:
 *   - status:       'idle' | 'running' | 'awaiting' | 'completed' | 'error'
 *   - phase:        'A' | 'B' | null     (which phase is in flight)
 *   - currentStepIndex: 0..PIPELINE_STEPS.length-1, advances over time
 *   - phaseAResponse / finalResult so /generate can render the right step
 *
 * Step progress within a phase is *simulated* against estimated durations
 * because the backend returns each phase as one atomic call. When the real
 * fetch resolves we snap the timeline to "all steps in this phase complete".
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, fetchStrategies, finalizeStrategy } from "../lib/api";
import { saveGeneratedAd } from "../lib/history";
import {
  FIRST_B_INDEX,
  PIPELINE_STEPS,
  stepIndexFromElapsed,
} from "./jobConstants";
import { JobContext } from "./jobContextInstance";

const initialState = {
  status: "idle", // 'idle' | 'running' | 'awaiting' | 'completed' | 'error'
  phase: null,
  currentStepIndex: 0,
  startedAt: null,
  campaignLabel: "",
  area: null,
  phaseAResponse: null,
  selectedIdx: null,
  finalResult: null,
  error: null,
  notification: null, // 'phase_a_done' | 'phase_b_done' (shown by indicator until acknowledged)
};

export function JobProvider({ children }) {
  const [state, setState] = useState(initialState);
  const phaseStartRef = useRef(null);
  const tickRef = useRef(null);
  const abortRef = useRef(null);

  const stopTimer = useCallback(() => {
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  const startTimer = useCallback(
    (phase) => {
      stopTimer();
      phaseStartRef.current = Date.now();
      tickRef.current = setInterval(() => {
        if (!phaseStartRef.current) return;
        const elapsed = Date.now() - phaseStartRef.current;
        const idx = stepIndexFromElapsed(phase, elapsed);
        setState((prev) => {
          if (prev.status !== "running" || prev.phase !== phase) return prev;
          if (prev.currentStepIndex >= idx) return prev;
          return { ...prev, currentStepIndex: idx };
        });
      }, 250);
    },
    [stopTimer],
  );

  // Cleanup on unmount.
  useEffect(
    () => () => {
      stopTimer();
      if (abortRef.current) abortRef.current.abort();
    },
    [stopTimer],
  );

  const reset = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    stopTimer();
    phaseStartRef.current = null;
    setState(initialState);
  }, [stopTimer]);

  const dismissNotification = useCallback(() => {
    setState((prev) =>
      prev.notification ? { ...prev, notification: null } : prev,
    );
  }, []);

  const dismissError = useCallback(() => {
    setState((prev) => (prev.error ? { ...prev, error: null } : prev));
  }, []);

  /* ------------------------------- Phase A ------------------------------- */

  const startPhaseA = useCallback(
    async ({ file, area, count = 2 }) => {
      if (state.status === "running") return;

      const controller = new AbortController();
      abortRef.current = controller;

      setState({
        ...initialState,
        status: "running",
        phase: "A",
        currentStepIndex: 0,
        startedAt: Date.now(),
        campaignLabel: file?.name || "Campaign",
        area: area || null,
      });

      startTimer("A");

      try {
        const data = await fetchStrategies({
          file,
          area,
          count,
          signal: controller.signal,
        });
        stopTimer();
        // Snap to the last step of phase A.
        setState((prev) => ({
          ...prev,
          status: "awaiting",
          phase: null,
          currentStepIndex: FIRST_B_INDEX - 1,
          phaseAResponse: data,
          selectedIdx: null,
          notification: "phase_a_done",
          error: null,
        }));
      } catch (err) {
        stopTimer();
        if (err?.name === "AbortError") {
          setState(initialState);
          return;
        }
        const apiErr =
          err instanceof ApiError
            ? err
            : new ApiError(String(err?.message || err));
        setState((prev) => ({
          ...prev,
          status: "error",
          phase: null,
          error: { phase: "A", message: apiErr.message, detail: apiErr.detail },
        }));
      } finally {
        abortRef.current = null;
      }
    },
    [startTimer, state.status, stopTimer],
  );

  /* ------------------------------- Phase B ------------------------------- */

  const setSelectedIdx = useCallback((idx) => {
    setState((prev) => {
      if (prev.status !== "awaiting") return prev;
      return { ...prev, selectedIdx: idx };
    });
  }, []);

  const startPhaseB = useCallback(async () => {
    if (
      state.status !== "awaiting" ||
      state.selectedIdx == null ||
      !state.phaseAResponse
    ) {
      return;
    }

    const phaseA = state.phaseAResponse;
    const selected = phaseA.strategies[state.selectedIdx];
    const controller = new AbortController();
    abortRef.current = controller;

    setState((prev) => ({
      ...prev,
      status: "running",
      phase: "B",
      currentStepIndex: FIRST_B_INDEX,
      finalResult: null,
      campaignLabel: selected?.featured_product?.product || prev.campaignLabel,
      error: null,
    }));

    startTimer("B");

    try {
      const data = await finalizeStrategy({
        selectedStrategy: selected,
        riskAnalysis: phaseA.risk_analysis,
        liveContext: phaseA.live_context,
        area: phaseA.metadata?.area,
        signal: controller.signal,
      });
      stopTimer();
      saveGeneratedAd({
        phaseAResponse: phaseA,
        selectedStrategy: selected,
        finalizeResponse: data,
      });
      setState((prev) => ({
        ...prev,
        status: "completed",
        phase: null,
        currentStepIndex: PIPELINE_STEPS.length - 1,
        finalResult: data,
        notification: "phase_b_done",
        error: null,
      }));
    } catch (err) {
      stopTimer();
      if (err?.name === "AbortError") return;
      const apiErr =
        err instanceof ApiError
          ? err
          : new ApiError(String(err?.message || err));
      setState((prev) => ({
        ...prev,
        status: "error",
        phase: null,
        error: { phase: "B", message: apiErr.message, detail: apiErr.detail },
      }));
    } finally {
      abortRef.current = null;
    }
  }, [
    startTimer,
    state.phaseAResponse,
    state.selectedIdx,
    state.status,
    stopTimer,
  ]);

  const value = useMemo(
    () => ({
      ...state,
      steps: PIPELINE_STEPS,
      actions: {
        startPhaseA,
        startPhaseB,
        setSelectedIdx,
        reset,
        dismissNotification,
        dismissError,
      },
    }),
    [
      state,
      startPhaseA,
      startPhaseB,
      setSelectedIdx,
      reset,
      dismissNotification,
      dismissError,
    ],
  );

  return <JobContext.Provider value={value}>{children}</JobContext.Provider>;
}
