// Single source of truth for mastery-level and skill colors.
// Used by RadarChart, profile/page, and quiz/results/page.

export const SKILL_COLORS: Record<string, string> = {
  not_started: "#94a3b8", // slate-400
  novice:      "#f87171", // red-400
  developing:  "#fb923c", // orange-400
  proficient:  "#60a5fa", // blue-400
  mastered:    "#34d399", // emerald-400
};

// Quiz results use a slightly different shade scale (500-level vs 400-level).
export const MASTERY_COLORS: Record<string, string> = {
  not_started: "#94a3b8", // slate-400
  novice:      "#ef4444", // red-500
  developing:  "#f97316", // orange-500
  proficient:  "#3b82f6", // blue-500
  mastered:    "#10b981", // emerald-500
};

export const BLOOM_COLORS: Record<string, string> = {
  remember:    "#ef4444", // red-500
  understand:  "#f97316", // orange-500
  apply:       "#3b82f6", // blue-500
  analyze:     "#8b5cf6", // violet-500
};

export const BRAND_PRIMARY = "#2563EB"; // primary-600

export function getSkillColor(level: string): string {
  return SKILL_COLORS[level] ?? BRAND_PRIMARY;
}

export function getMasteryColor(level: string): string {
  return MASTERY_COLORS[level] ?? BRAND_PRIMARY;
}
