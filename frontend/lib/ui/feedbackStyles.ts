// Quiz answer button feedback styles — single source for correct/incorrect/selected states.

interface OptionStyleResult {
  borderColor: string;
  background: string;
  textColor: string;
  badgeBg: string;
  badgeColor: string;
}

export function getOptionStyle(opts: {
  isFeedback: boolean;
  isCorrect: boolean;
  isWrong: boolean;
  isSelected: boolean;
}): OptionStyleResult {
  const { isFeedback, isCorrect, isWrong, isSelected } = opts;

  if (isFeedback && isCorrect) {
    return {
      borderColor: "var(--state-success-border)",
      background:  "var(--state-success-bg)",
      textColor:   "var(--state-success-fg)",
      badgeBg:     "var(--state-success-fg)",
      badgeColor:  "white",
    };
  }

  if (isFeedback && isWrong) {
    return {
      borderColor: "var(--state-error-border)",
      background:  "var(--state-error-bg)",
      textColor:   "var(--state-error-fg)",
      badgeBg:     "var(--state-error-fg)",
      badgeColor:  "white",
    };
  }

  if (isSelected) {
    return {
      borderColor: "var(--color-primary-500, #3b82f6)",
      background:  "var(--color-primary-50, #eff6ff)",
      textColor:   "var(--text-primary)",
      badgeBg:     "var(--color-primary-500, #3b82f6)",
      badgeColor:  "white",
    };
  }

  return {
    borderColor: "var(--border)",
    background:  "var(--bg-elevated)",
    textColor:   "var(--text-primary)",
    badgeBg:     "var(--bg-secondary)",
    badgeColor:  "var(--text-muted)",
  };
}
