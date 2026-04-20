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
      borderColor: "#22c55e", // green-500
      background:  "#f0fdf4", // green-50
      textColor:   "#15803d", // green-700
      badgeBg:     "#22c55e",
      badgeColor:  "white",
    };
  }

  if (isFeedback && isWrong) {
    return {
      borderColor: "#ef4444", // red-500
      background:  "#fef2f2", // red-50
      textColor:   "#b91c1c", // red-700
      badgeBg:     "#ef4444",
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
