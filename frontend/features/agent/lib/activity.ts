export type AgentActivityStepId = "understanding" | "searching" | "reading" | "composing";

export type AgentActivityStep = {
  id: AgentActivityStepId;
  title: string;
  detail?: string;
};

export type AgentActivityThought = {
  user_goal: string;
  active_topic?: string | null;
  evidence_need: string;
  tool_plan: string[];
};

export type AgentActivitySnapshot = {
  message: string;
  startedAt: number;
  completedAt?: number;
  steps: AgentActivityStep[];
};

const STEP_ORDER: AgentActivityStepId[] = ["understanding", "searching", "reading", "composing"];

const DEFAULT_STEPS: Record<AgentActivityStepId, string> = {
  understanding: "Understanding your question",
  searching: "Searching course content",
  reading: "Reading sources",
  composing: "Composing answer",
};

export function formatAgentActivityDuration(ms: number) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  if (minutes === 0) {
    return `${seconds}s`;
  }

  return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
}

export function getAgentActivityHeader({
  elapsedMs,
  completed,
}: {
  elapsedMs: number;
  completed: boolean;
}) {
  const duration = formatAgentActivityDuration(elapsedMs);
  return completed ? `Thought for ${duration}` : `Thinking · ${duration}`;
}

export function getAgentActivityElapsedMs(activity: AgentActivitySnapshot, now = Date.now()) {
  return Math.max(0, (activity.completedAt ?? now) - activity.startedAt);
}

export function createAgentActivity({
  message,
  startedAt = Date.now(),
}: {
  message: string;
  startedAt?: number;
}): AgentActivitySnapshot {
  return {
    message,
    startedAt,
    steps: [
      {
        id: "understanding",
        title: DEFAULT_STEPS.understanding,
      },
    ],
  };
}

export function applyAgentActivityThought(
  activity: AgentActivitySnapshot,
  thought: AgentActivityThought,
): AgentActivitySnapshot {
  const topic = thought.active_topic?.trim() || thought.user_goal.trim() || activity.message.trim();
  let next = upsertStep(activity, {
    id: "understanding",
    title: DEFAULT_STEPS.understanding,
    detail: topic ? `Topic: ${topic}` : undefined,
  });

  for (const planStep of thought.tool_plan) {
    const normalized = planStep.replace(/_/g, " ").toLowerCase();
    if (normalized.includes("search")) {
      next = upsertSearchStep(next, topic);
    } else if (normalized.includes("read") || normalized.includes("source") || normalized.includes("evidence")) {
      next = upsertStep(next, {
        id: "reading",
        title: DEFAULT_STEPS.reading,
        detail: "Using available source evidence",
      });
    } else if (normalized.includes("compose") || normalized.includes("answer") || normalized.includes("respond")) {
      next = upsertStep(next, {
        id: "composing",
        title: DEFAULT_STEPS.composing,
        detail: "Preparing grounded response",
      });
    }
  }

  return next;
}

export function applyAgentActivityStatus(activity: AgentActivitySnapshot, status: string): AgentActivitySnapshot {
  const normalized = status.toLowerCase();
  const topic = getActivityTopic(activity);

  if (normalized.includes("search")) {
    const title =
      normalized.includes("web") || normalized.includes("paper")
        ? "Searching web and papers"
        : DEFAULT_STEPS.searching;
    return upsertSearchStep(activity, topic, title);
  }

  if (normalized.includes("read") || normalized.includes("source") || normalized.includes("citation")) {
    return upsertStep(activity, {
      id: "reading",
      title: DEFAULT_STEPS.reading,
      detail: "Using available source evidence",
    });
  }

  if (normalized.includes("compos") || normalized.includes("answer") || normalized.includes("ground")) {
    return upsertStep(activity, {
      id: "composing",
      title: DEFAULT_STEPS.composing,
      detail: getComposingDetail(activity),
    });
  }

  if (normalized.includes("analy") || normalized.includes("prepar") || normalized.includes("understand")) {
    return upsertStep(activity, {
      id: "understanding",
      title: DEFAULT_STEPS.understanding,
      detail: getUnderstandingDetail(activity),
    });
  }

  return activity;
}

export function completeAgentActivity(
  activity: AgentActivitySnapshot,
  {
    completedAt = Date.now(),
    citationCount = 0,
  }: {
    completedAt?: number;
    citationCount?: number;
  } = {},
): AgentActivitySnapshot {
  return upsertStep(
    {
      ...activity,
      completedAt,
    },
    {
      id: "composing",
      title: DEFAULT_STEPS.composing,
      detail:
        citationCount > 0
          ? `Grounding response with ${citationCount} ${citationCount === 1 ? "citation" : "citations"}`
          : "Preparing grounded response",
    },
  );
}

function upsertSearchStep(activity: AgentActivitySnapshot, topic: string, title = DEFAULT_STEPS.searching) {
  return upsertStep(activity, {
    id: "searching",
    title,
    detail: topic ? `Query: "${topic}"` : undefined,
  });
}

function upsertStep(activity: AgentActivitySnapshot, step: AgentActivityStep): AgentActivitySnapshot {
  const stepsById = new Map(activity.steps.map((item) => [item.id, item]));
  stepsById.set(step.id, { ...stepsById.get(step.id), ...step });

  return {
    ...activity,
    steps: STEP_ORDER.map((id) => stepsById.get(id)).filter((item): item is AgentActivityStep => Boolean(item)),
  };
}

function getActivityTopic(activity: AgentActivitySnapshot) {
  const understanding = activity.steps.find((step) => step.id === "understanding");
  const topic = understanding?.detail?.replace(/^Topic:\s*/i, "").trim();
  return topic || activity.message.trim();
}

function getUnderstandingDetail(activity: AgentActivitySnapshot) {
  const topic = getActivityTopic(activity);
  return topic ? `Topic: ${topic}` : undefined;
}

function getComposingDetail(activity: AgentActivitySnapshot) {
  return activity.steps.find((step) => step.id === "composing")?.detail ?? "Preparing grounded response";
}
