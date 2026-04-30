export interface PlannerReasonDescription {
  label: string;
  details: string;
}

export function describePlannerReason(code: string): PlannerReasonDescription {
  switch (code) {
    case "critical_kp":
      return {
        label: "Critical KP",
        details: "This unit covers a critical knowledge point for the current path.",
      };
    case "high_salience":
      return {
        label: "High salience",
        details: "This content is highly relevant to the learning goal.",
      };
    case "quiz_available":
      return {
        label: "Quiz available",
        details: "Suitable assessment questions are available to verify mastery.",
      };
    case "required_prerequisite":
      return {
        label: "Prerequisite",
        details: "This is a required foundation before the next part.",
      };
    case "quick_review":
      return {
        label: "Quick review",
        details: "Mastery is fairly solid, so only a quick review is needed.",
      };
    case "skip_by_mastery":
      return {
        label: "Skip by mastery",
        details: "There is strong enough evidence to skip this content.",
      };
    case "hidden_logistics":
      return {
        label: "Hidden logistics",
        details: "Excluded from the main path because it is logistics/admin content, not a learner skip.",
      };
    case "reference_only":
      return {
        label: "Reference",
        details: "Reference content that is not required for learning or quizzes in the main path.",
      };
    default:
      return {
        label: code,
        details: "The planner does not have a custom description for this reason code yet.",
      };
  }
}
