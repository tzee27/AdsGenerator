import { useContext } from 'react';
import { JobContext } from './jobContextInstance';

export function useJob() {
  const ctx = useContext(JobContext);
  if (!ctx) {
    throw new Error('useJob must be used inside <JobProvider>');
  }
  return ctx;
}
