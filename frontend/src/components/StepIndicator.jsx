import '../styles/StepIndicator.css';

export default function StepIndicator({ steps, currentStep }) {
  return (
    <div className="step-indicator">
      {steps.map((label, idx) => {
        const stepNum = idx + 1;
        const isCompleted = stepNum < currentStep;
        const isActive = stepNum === currentStep;

        return (
          <div key={idx} className="step-indicator__item">
            <div className={`step-indicator__circle ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''}`}>
              {isCompleted ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : (
                <span>{stepNum}</span>
              )}
            </div>
            <span className={`step-indicator__label ${isActive ? 'active' : ''}`}>{label}</span>
            {idx < steps.length - 1 && (
              <div className={`step-indicator__line ${isCompleted ? 'completed' : ''}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
