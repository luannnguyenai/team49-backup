# Learn Roadmap Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current generic graph view on `/learn` with a roadmap.sh-inspired planner that renders only a concrete selected learning path. V1 supports exactly two path topologies: Deep Learning -> Computer Vision and Deep Learning -> NLP.

**Architecture:** Treat onboarding/path selection as an input provider and `/learn` as the stable planner surface. Add a small frontend path profile contract, convert existing `PathItemResponse[]` into a deterministic roadmap layout model, and render SVG connectors plus interactive HTML nodes only after a concrete path has been selected/generated. Keep the existing learning path API, Zustand store, timeline view, and drawer behavior intact for V1.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript 5, Zustand, Tailwind CSS, Vitest, Testing Library, existing FastAPI `/api/learning-path` contract.

---

## Implementation Surface

**Frontend files**
- Create: `frontend/features/learning-path/profile.ts`
- Create: `frontend/features/learning-path/roadmap-model.ts`
- Create: `frontend/features/learning-path/components/PlannerHeader.tsx`
- Create: `frontend/features/learning-path/components/PathRequiredState.tsx`
- Create: `frontend/features/learning-path/components/RoadmapPlanner.tsx`
- Create: `frontend/features/learning-path/components/RoadmapConnectorLayer.tsx`
- Create: `frontend/features/learning-path/components/RoadmapNodeCard.tsx`
- Modify: `frontend/features/learning-path/components/LearningPathShell.tsx`
- Modify: `frontend/features/learning-path/components/RoadmapCanvas.tsx`
- Modify: `frontend/features/learning-path/store.ts`
- Modify: `frontend/features/learning-path/presenters.ts`
- Modify: `frontend/types/index.ts`

**Test files**
- Create: `frontend/tests/unit/learning-path/profile.test.ts`
- Create: `frontend/tests/unit/learning-path/roadmap-model.test.ts`
- Create: `frontend/tests/unit/learning-path/roadmap-components.test.tsx`
- Modify: `frontend/tests/unit/learning-path/presenters.test.ts`
- Modify: `frontend/tests/unit/learning-path/status.test.ts`

## Core Decisions

- `/learn` remains the planner entry point.
- Onboarding is only an input provider. It should output a `LearningProfile`; the planner should not depend on onboarding step structure.
- Planner V1 uses the existing `/api/learning-path` and `/api/learning-path/timeline` endpoints.
- Planner ranking should move toward schema-v2-aware decisions: prerequisite graph for bridge insertion, `unit_kp_map` for mastery coverage, and canonical unit fields for salience, content type, quiz availability, worth-learning, and critical KP overrides.
- Planner skip/bridge decisions must be evidence-backed. Self-reported onboarding prior can influence path selection and pacing, but it must not count as mastery for skip, waive, or bridge decisions.
- Return-user UX should be state-driven: use session/progress/mastery timestamps to resume unfinished work, surface review, or request placement-lite when mastery is stale.
- Content segment policy must prevent logistics/admin/reference-only segments from receiving core learning UX such as quiz, skip, or bridge prompts.
- The roadmap renderer must be data-driven. Do not paste the raw roadmap.sh SVG/body into the app.
- ReactFlow remains installed, but the planner graph view should be custom SVG connectors plus HTML nodes because the target visual language is a learning roadmap, not a graph editor.
- V1 supports only two explicit path keys: `dl_cv` and `dl_nlp`.
- Do not render a default roadmap when the user has not selected/generated a path.
- Do not support a combined CV+NLP path in V1. If onboarding emits both CV and NLP intent, block with a validation error and ask the user to choose one.
- If no concrete path is available, `/learn` shows a path-required empty state with CTA to onboarding/path selection.
- If the future onboarding/profile changes from CV to NLP, preserve completed progress in historical runtime state and only mark the rendered path as stale until the backend replan endpoint exists.
- V1 does not add a backend migration. Backend enrichment can be implemented against existing schema v2 tables and existing planner endpoints before adding a dedicated replan endpoint.

## Runtime Contracts

Add this frontend profile contract:

```ts
export type PlannerPathKey = "dl_cv" | "dl_nlp";

export interface LearningProfile {
  pathKey: PlannerPathKey;
  label: string;
  startCourse: string | null;
  selectedCourseIds: string[];
  weeklyHours: number | null;
  source: "onboarding" | "manual";
  topologyHash: string;
  pacingHash: string;
  generatedFromProfileHash: string;
}
```

Supported V1 path profiles:

```ts
export const SUPPORTED_LEARNING_PATHS = {
  dl_cv: {
    pathKey: "dl_cv",
    label: "Deep Learning -> Computer Vision",
    startCourse: "CS230",
    selectedCourseIds: ["CS230", "CS231n"],
  },
  dl_nlp: {
    pathKey: "dl_nlp",
    label: "Deep Learning -> NLP",
    startCourse: "CS230",
    selectedCourseIds: ["CS230", "CS224n"],
  },
};
```

Implementation must compute hashes from helper functions. Do not add a `dl_cv_nlp` or default profile in V1.

Future onboarding/path-selection adapter contract:

```ts
export interface OnboardingLearningProfileInput {
  selected_path_key: unknown;
  available_hours_per_week: number | null;
  preferred_method?: "reading" | "video" | null;
}

export function isPlannerPathKey(value: unknown): value is PlannerPathKey {
  return value === "dl_cv" || value === "dl_nlp";
}

export function onboardingToLearningProfile(
  input: OnboardingLearningProfileInput,
): LearningProfile;
```

Roadmap model contract:

```ts
export type RoadmapNodeKind = "topic" | "unit";

export interface RoadmapNodeModel {
  id: string;
  kind: RoadmapNodeKind;
  title: string;
  subtitle: string | null;
  x: number;
  y: number;
  width: number;
  height: number;
  status: "pending" | "in_progress" | "completed" | "skipped";
  recommended: boolean;
  item: PathItemResponse | null;
  itemId: string | null;
  sectionKey: string | null;
}

export interface RoadmapConnectorModel {
  id: string;
  from: string;
  to: string;
  path: string;
  active: boolean;
}

export interface RoadmapModel {
  width: number;
  height: number;
  nodes: RoadmapNodeModel[];
  connectors: RoadmapConnectorModel[];
}
```

Schema v2 planner metadata contract:

```ts
export type PlannerReasonCode =
  | "required_prerequisite"
  | "critical_kp"
  | "high_salience"
  | "quiz_available"
  | "quick_review"
  | "skip_by_mastery"
  | "optional_low_salience"
  | "reference_only"
  | "hidden_logistics"
  | "mastery_stale"
  | "evidence_required"
  | "review_due";

export interface PlannerUnitReason {
  reasonCode: PlannerReasonCode;
  label: string;
  details: string;
}
```

## Task 1: Add Learning Profile Contract

**Files:**
- Create: `frontend/features/learning-path/profile.ts`
- Create: `frontend/tests/unit/learning-path/profile.test.ts`

- [ ] **Step 1: Write failing tests for concrete path profiles and onboarding adapter**

Create `frontend/tests/unit/learning-path/profile.test.ts`:

```ts
import {
  SUPPORTED_LEARNING_PATHS,
  createLearningProfileForPath,
  onboardingToLearningProfile,
  profileHash,
} from "@/features/learning-path/profile";

describe("learning path profile contract", () => {
  it("defines only the two V1 supported concrete paths", () => {
    expect(Object.keys(SUPPORTED_LEARNING_PATHS)).toEqual(["dl_cv", "dl_nlp"]);
    expect(SUPPORTED_LEARNING_PATHS.dl_cv).toMatchObject({
      pathKey: "dl_cv",
      startCourse: "CS230",
      selectedCourseIds: ["CS230", "CS231n"],
    });
    expect(SUPPORTED_LEARNING_PATHS.dl_nlp).toMatchObject({
      pathKey: "dl_nlp",
      startCourse: "CS230",
      selectedCourseIds: ["CS230", "CS224n"],
    });
  });

  it("creates a stable profile for one selected path only", () => {
    const profile = createLearningProfileForPath("dl_cv", {
      weeklyHours: 6,
      source: "manual",
    });

    expect(profile).toMatchObject({
      pathKey: "dl_cv",
      label: "Deep Learning -> Computer Vision",
      startCourse: "CS230",
      selectedCourseIds: ["CS230", "CS231n"],
      weeklyHours: 6,
      source: "manual",
    });
    expect(profile.generatedFromProfileHash).toBe(profileHash(profile));
  });

  it("maps onboarding output into a stable planner profile", () => {
    const profile = onboardingToLearningProfile({
      selected_path_key: "dl_nlp",
      available_hours_per_week: 6,
      preferred_method: "video",
    });

    expect(profile).toMatchObject({
      pathKey: "dl_nlp",
      label: "Deep Learning -> NLP",
      startCourse: "CS230",
      selectedCourseIds: ["CS230", "CS224n"],
      weeklyHours: 6,
      source: "onboarding",
    });
    expect(profile.generatedFromProfileHash).toBe(profileHash(profile));
  });

  it("rejects invalid or combined path keys at runtime", () => {
    expect(() =>
      onboardingToLearningProfile({
        selected_path_key: "dl_cv_nlp",
        available_hours_per_week: 6,
      }),
    ).toThrow(/requires exactly one path/i);
  });
});
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
cd frontend
npm test -- --run tests/unit/learning-path/profile.test.ts
```

Expected: FAIL because `profile.ts` does not exist.

- [ ] **Step 3: Implement `profile.ts`**

Create `frontend/features/learning-path/profile.ts`:

```ts
export type PlannerPathKey = "dl_cv" | "dl_nlp";

export interface LearningProfile {
  pathKey: PlannerPathKey;
  label: string;
  startCourse: string | null;
  selectedCourseIds: string[];
  weeklyHours: number | null;
  source: "onboarding" | "manual";
  topologyHash: string;
  pacingHash: string;
  generatedFromProfileHash: string;
}

export interface OnboardingLearningProfileInput {
  selected_path_key: PlannerPathKey;
  available_hours_per_week: number | null;
  preferred_method?: "reading" | "video" | null;
}

function normalizeCourseId(courseId: string): string {
  const trimmed = courseId.trim();
  const lower = trimmed.toLowerCase();
  if (lower === "cs230") return "CS230";
  if (lower === "cs231n") return "CS231n";
  if (lower === "cs224n") return "CS224n";
  return trimmed;
}

function normalizeCourseIdsPreserveOrder(courseIds: string[]): string[] {
  return [...new Set(courseIds.map(normalizeCourseId).filter(Boolean))];
}

function normalizeCourseIdsForHash(courseIds: string[]): string[] {
  return normalizeCourseIdsPreserveOrder(courseIds).sort();
}

export type ProfileHashInput = Pick<
  LearningProfile,
  "source" | "pathKey" | "startCourse" | "selectedCourseIds" | "weeklyHours"
>;

export function topologyHash(profile: ProfileHashInput): string {
  return [
    profile.source,
    profile.pathKey,
    profile.startCourse ?? "none",
    normalizeCourseIdsForHash(profile.selectedCourseIds).join(","),
  ].join(":");
}

export function pacingHash(profile: ProfileHashInput): string {
  return [
    "weekly",
    profile.weeklyHours ?? "flex",
  ].join(":");
}

export function profileHash(profile: ProfileHashInput): string {
  return topologyHash(profile);
}

function withHashes(base: ProfileHashInput & { label: string }): LearningProfile {
  const normalizedBase = {
    ...base,
    selectedCourseIds: normalizeCourseIdsPreserveOrder(base.selectedCourseIds),
    startCourse: base.startCourse ? normalizeCourseId(base.startCourse) : null,
  };
  const nextTopologyHash = topologyHash(normalizedBase);
  return {
    ...normalizedBase,
    topologyHash: nextTopologyHash,
    pacingHash: pacingHash(normalizedBase),
    generatedFromProfileHash: nextTopologyHash,
  };
}

export const SUPPORTED_LEARNING_PATHS = {
  dl_cv: {
    pathKey: "dl_cv",
    label: "Deep Learning -> Computer Vision",
    startCourse: "CS230",
    selectedCourseIds: ["CS230", "CS231n"],
  },
  dl_nlp: {
    pathKey: "dl_nlp",
    label: "Deep Learning -> NLP",
    startCourse: "CS230",
    selectedCourseIds: ["CS230", "CS224n"],
  },
} as const satisfies Record<PlannerPathKey, {
  pathKey: PlannerPathKey;
  label: string;
  startCourse: string;
  selectedCourseIds: string[];
}>;

export function createLearningProfileForPath(
  pathKey: PlannerPathKey,
  options: {
    weeklyHours: number | null;
    source: LearningProfile["source"];
  },
): LearningProfile {
  const path = SUPPORTED_LEARNING_PATHS[pathKey];
  return withHashes({
    pathKey,
    label: path.label,
    startCourse: path.startCourse,
    selectedCourseIds: [...path.selectedCourseIds],
    weeklyHours: options.weeklyHours,
    source: options.source,
  });
}

export function onboardingToLearningProfile(
  input: OnboardingLearningProfileInput,
): LearningProfile {
  if (!isPlannerPathKey(input.selected_path_key)) {
    throw new Error("Planner V1 requires exactly one path: dl_cv or dl_nlp");
  }

  return createLearningProfileForPath(input.selected_path_key, {
    weeklyHours: input.available_hours_per_week,
    source: "onboarding",
  });
}
```

- [ ] **Step 4: Run the profile tests**

Run:

```bash
cd frontend
npm test -- --run tests/unit/learning-path/profile.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/features/learning-path/profile.ts frontend/tests/unit/learning-path/profile.test.ts
git commit -m "feat: add learning profile contract"
```

## Task 2: Build Roadmap Layout Model From Existing Path Items

**Files:**
- Create: `frontend/features/learning-path/roadmap-model.ts`
- Create: `frontend/tests/unit/learning-path/roadmap-model.test.ts`
- Modify: `frontend/features/learning-path/presenters.ts`

- [ ] **Step 1: Write failing roadmap model tests**

Create `frontend/tests/unit/learning-path/roadmap-model.test.ts`:

```ts
import { buildRoadmapModel } from "@/features/learning-path/roadmap-model";
import type { PathItemResponse } from "@/types";

const items: PathItemResponse[] = [
  {
    id: "path-1",
    learning_unit_id: "unit-1",
    learning_unit_title: "Neural Networks Basics",
    section_title: "CS230",
    action: "standard_learn",
    estimated_hours: 1.5,
    order_index: 1,
    week_number: 1,
    status: "completed",
    canonical_unit_id: "canonical-1",
  },
  {
    id: "path-2",
    learning_unit_id: "unit-2",
    learning_unit_title: "CNN Architectures",
    section_title: "CS231n",
    action: "standard_learn",
    estimated_hours: 2,
    order_index: 2,
    week_number: 1,
    status: "pending",
    canonical_unit_id: "canonical-2",
  },
  {
    id: "path-3",
    learning_unit_id: "unit-3",
    learning_unit_title: "Attention",
    section_title: "CS224n",
    action: "standard_learn",
    estimated_hours: 2,
    order_index: 3,
    week_number: 2,
    status: "pending",
    canonical_unit_id: "canonical-3",
  },
];

describe("buildRoadmapModel", () => {
  it("creates topic and unit nodes in order", () => {
    const model = buildRoadmapModel(items);

    expect(model.nodes.map((node) => node.id)).toEqual([
      "topic-section-1-cs230",
      "unit-path-1",
      "topic-section-2-cs231n",
      "unit-path-2",
      "topic-section-3-cs224n",
      "unit-path-3",
    ]);
    expect(model.width).toBeGreaterThan(900);
    expect(model.height).toBeGreaterThan(500);
    expect(model.nodes.find((node) => node.id === "unit-path-2")?.item).toMatchObject({
      id: "path-2",
    });
    expect(model.nodes.find((node) => node.id === "topic-section-2-cs231n")?.y).toBeGreaterThan(
      model.nodes.find((node) => node.id === "unit-path-1")?.y ?? 0,
    );
  });

  it("marks the first pending non-skip unit as recommended", () => {
    const model = buildRoadmapModel(items);
    const recommended = model.nodes.filter((node) => node.recommended);

    expect(recommended).toHaveLength(1);
    expect(recommended[0]).toMatchObject({
      id: "unit-path-2",
      title: "CNN Architectures",
    });
  });

  it("creates active connectors up to the recommended unit", () => {
    const model = buildRoadmapModel(items);

    expect(model.connectors).toHaveLength(5);
    expect(model.connectors[0].path).toMatch(/^M /);
    expect(model.connectors.some((connector) => connector.active)).toBe(true);
  });
});
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
cd frontend
npm test -- --run tests/unit/learning-path/roadmap-model.test.ts
```

Expected: FAIL because `roadmap-model.ts` does not exist.

- [ ] **Step 3: Implement `roadmap-model.ts`**

Create `frontend/features/learning-path/roadmap-model.ts`:

```ts
import type { PathItemResponse, PathStatus } from "@/types";
import { computeRecommendedNext, pathToFlow, sortByOrder } from "./presenters";

export type RoadmapNodeKind = "topic" | "unit";

export interface RoadmapNodeModel {
  id: string;
  kind: RoadmapNodeKind;
  title: string;
  subtitle: string | null;
  x: number;
  y: number;
  width: number;
  height: number;
  status: PathStatus;
  recommended: boolean;
  item: PathItemResponse | null;
  itemId: string | null;
  sectionKey: string | null;
}

export interface RoadmapConnectorModel {
  id: string;
  from: string;
  to: string;
  path: string;
  active: boolean;
}

export interface RoadmapModel {
  width: number;
  height: number;
  nodes: RoadmapNodeModel[];
  connectors: RoadmapConnectorModel[];
}

const TOPIC_WIDTH = 220;
const TOPIC_HEIGHT = 54;
const UNIT_WIDTH = 360;
const UNIT_HEIGHT = 76;
const COLUMN_GAP = 96;
const UNIT_ROW_GAP = 22;
const SECTION_GAP = 86;
const START_X = 72;
const START_Y = 48;
const LANES = 2;

function connectorPath(from: RoadmapNodeModel, to: RoadmapNodeModel): string {
  if (to.x <= from.x + from.width) {
    const fromX = from.x + from.width / 2;
    const fromY = from.y + from.height;
    const toX = to.x + to.width / 2;
    const toY = to.y;
    const midY = fromY + (toY - fromY) / 2;
    return `M ${fromX} ${fromY} C ${fromX} ${midY}, ${toX} ${midY}, ${toX} ${toY}`;
  }

  const fromX = from.x + from.width;
  const fromY = from.y + from.height / 2;
  const toX = to.x;
  const toY = to.y + to.height / 2;
  const midX = fromX + (toX - fromX) / 2;
  return `M ${fromX} ${fromY} C ${midX} ${fromY}, ${midX} ${toY}, ${toX} ${toY}`;
}

function unitPositionInSection(sectionTop: number, indexInSection: number): Pick<RoadmapNodeModel, "x" | "y"> {
  const row = Math.floor(indexInSection / LANES);
  const lane = indexInSection % LANES;
  return {
    x: START_X + lane * (UNIT_WIDTH + COLUMN_GAP),
    y: sectionTop + TOPIC_HEIGHT + 28 + row * (UNIT_HEIGHT + UNIT_ROW_GAP),
  };
}

export function buildRoadmapModel(items: PathItemResponse[]): RoadmapModel {
  const ordered = sortByOrder(items);
  if (ordered.length === 0) {
    return { width: 1000, height: 520, nodes: [], connectors: [] };
  }

  const recommendedId = computeRecommendedNext(ordered);
  const flow = pathToFlow(ordered);
  const nodes: RoadmapNodeModel[] = [];
  let sectionTop = START_Y;

  for (const section of flow.sectionSummaries) {
    nodes.push({
      id: `topic-${section.key}`,
      kind: "topic",
      title: section.title,
      subtitle: `${section.items.length} bài học`,
      width: TOPIC_WIDTH,
      height: TOPIC_HEIGHT,
      x: START_X,
      y: sectionTop,
      status: section.items.every((item) => item.status === "completed") ? "completed" : "pending",
      recommended: false,
      item: null,
      itemId: null,
      sectionKey: section.key,
    });

    for (const [indexInSection, item] of section.items.entries()) {
      const unitPosition = unitPositionInSection(sectionTop, indexInSection);
      nodes.push({
        id: `unit-${item.id}`,
        kind: "unit",
        title: item.learning_unit_title,
        subtitle: item.week_number ? `Tuần ${item.week_number}` : item.action.replaceAll("_", " "),
        width: UNIT_WIDTH,
        height: UNIT_HEIGHT,
        x: unitPosition.x,
        y: unitPosition.y,
        status: item.status,
        recommended: item.id === recommendedId,
        item,
        itemId: item.id,
        sectionKey: null,
      });
    }

    const unitRows = Math.max(1, Math.ceil(section.items.length / LANES));
    sectionTop += TOPIC_HEIGHT + 28 + unitRows * UNIT_HEIGHT + (unitRows - 1) * UNIT_ROW_GAP + SECTION_GAP;
  }

  const connectors: RoadmapConnectorModel[] = [];
  for (let index = 0; index < nodes.length - 1; index += 1) {
    const from = nodes[index];
    const to = nodes[index + 1];
    connectors.push({
      id: `${from.id}-${to.id}`,
      from: from.id,
      to: to.id,
      path: connectorPath(from, to),
      active: from.status === "completed" || to.recommended,
    });
  }

  const width = Math.max(...nodes.map((node) => node.x + node.width), 1000) + START_X;
  const height = Math.max(...nodes.map((node) => node.y + node.height), 520) + START_Y;

  return { width, height, nodes, connectors };
}
```

- [ ] **Step 4: Export the model helpers**

If imports require a barrel export in this codebase, add exports from `frontend/features/learning-path/presenters.ts` only for existing helpers already used by `roadmap-model.ts`. Do not move ReactFlow-specific types into `roadmap-model.ts`.

- [ ] **Step 5: Run roadmap model tests**

Run:

```bash
cd frontend
npm test -- --run tests/unit/learning-path/roadmap-model.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/features/learning-path/roadmap-model.ts frontend/tests/unit/learning-path/roadmap-model.test.ts frontend/features/learning-path/presenters.ts
git commit -m "feat: add roadmap planner model"
```

## Task 3: Build Roadmap UI Components

**Files:**
- Create: `frontend/features/learning-path/components/PlannerHeader.tsx`
- Create: `frontend/features/learning-path/components/PathRequiredState.tsx`
- Create: `frontend/features/learning-path/components/RoadmapConnectorLayer.tsx`
- Create: `frontend/features/learning-path/components/RoadmapNodeCard.tsx`
- Create: `frontend/features/learning-path/components/RoadmapPlanner.tsx`
- Create: `frontend/tests/unit/learning-path/roadmap-components.test.tsx`

- [ ] **Step 1: Write component tests**

Create `frontend/tests/unit/learning-path/roadmap-components.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PathRequiredState from "@/features/learning-path/components/PathRequiredState";
import RoadmapPlanner from "@/features/learning-path/components/RoadmapPlanner";
import type { PathItemResponse } from "@/types";

const items: PathItemResponse[] = [
  {
    id: "path-1",
    learning_unit_id: "unit-1",
    learning_unit_title: "Neural Networks Basics",
    section_title: "CS230",
    action: "standard_learn",
    estimated_hours: 1.5,
    order_index: 1,
    week_number: 1,
    status: "completed",
    canonical_unit_id: "canonical-1",
  },
  {
    id: "path-2",
    learning_unit_id: "unit-2",
    learning_unit_title: "CNN Architectures",
    section_title: "CS231n",
    action: "standard_learn",
    estimated_hours: 2,
    order_index: 2,
    week_number: 1,
    status: "pending",
    canonical_unit_id: "canonical-2",
  },
];

describe("roadmap planner components", () => {
  it("renders a path-required state instead of a default roadmap", () => {
    render(<PathRequiredState />);

    expect(screen.getByText(/chọn một lộ trình/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /chọn lộ trình/i })).toHaveAttribute(
      "href",
      "/onboarding?next=/learn",
    );
  });

  it("opens the selected item when a unit node is clicked", async () => {
    const user = userEvent.setup();
    const onSelectItem = vi.fn();
    const onSelectSection = vi.fn();

    render(
      <RoadmapPlanner
        items={items}
        onSelectItem={onSelectItem}
        onSelectSection={onSelectSection}
      />,
    );

    await user.click(screen.getByRole("button", { name: /CNN Architectures/i }));

    expect(onSelectItem).toHaveBeenCalledWith("path-2");
    expect(onSelectSection).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run component tests and verify they fail**

Run:

```bash
cd frontend
npm test -- --run tests/unit/learning-path/roadmap-components.test.tsx
```

Expected: FAIL because components do not exist.

- [ ] **Step 3: Implement `PathRequiredState`**

Create `frontend/features/learning-path/components/PathRequiredState.tsx`:

```tsx
"use client";

import Link from "next/link";
import { MapIcon } from "lucide-react";

export default function PathRequiredState() {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white px-6 py-10 text-center">
      <div className="mx-auto flex max-w-xl flex-col items-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
          <MapIcon className="h-6 w-6" aria-hidden="true" />
        </span>
        <h2 className="mt-4 text-xl font-black text-slate-950">Chọn một lộ trình để bắt đầu</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Planner V1 chỉ render lộ trình cụ thể. Hiện hỗ trợ hai path riêng: Deep Learning -> Computer Vision
          hoặc Deep Learning -> NLP. Không có default path và không có path gộp CV+NLP.
        </p>
        <Link
          href="/onboarding?next=/learn"
          className="mt-5 inline-flex min-h-11 items-center justify-center rounded-xl bg-blue-600 px-5 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Chọn lộ trình
        </Link>
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Implement `RoadmapConnectorLayer`**

Create `frontend/features/learning-path/components/RoadmapConnectorLayer.tsx`:

```tsx
import type { RoadmapConnectorModel } from "../roadmap-model";

interface RoadmapConnectorLayerProps {
  width: number;
  height: number;
  connectors: RoadmapConnectorModel[];
}

export default function RoadmapConnectorLayer({
  width,
  height,
  connectors,
}: RoadmapConnectorLayerProps) {
  return (
    <svg
      aria-hidden="true"
      className="pointer-events-none absolute inset-0"
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
    >
      {connectors.map((connector) => (
        <path
          key={connector.id}
          d={connector.path}
          fill="none"
          stroke={connector.active ? "#2563eb" : "#cbd5e1"}
          strokeWidth={connector.active ? 4 : 3}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeDasharray={connector.active ? undefined : "8 10"}
        />
      ))}
    </svg>
  );
}
```

- [ ] **Step 5: Implement `RoadmapNodeCard`**

Create `frontend/features/learning-path/components/RoadmapNodeCard.tsx`:

```tsx
"use client";

import { Check, Circle, Lock, Play, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RoadmapNodeModel } from "../roadmap-model";

interface RoadmapNodeCardProps {
  node: RoadmapNodeModel;
  onSelectItem: (id: string) => void;
  onSelectSection: (sectionKey: string) => void;
}

function statusIcon(status: RoadmapNodeModel["status"], recommended: boolean) {
  if (status === "completed") return <Check className="h-4 w-4" aria-hidden="true" />;
  if (status === "skipped") return <RotateCcw className="h-4 w-4" aria-hidden="true" />;
  if (recommended || status === "in_progress") return <Play className="h-4 w-4" aria-hidden="true" />;
  return <Lock className="h-4 w-4" aria-hidden="true" />;
}

export default function RoadmapNodeCard({
  node,
  onSelectItem,
  onSelectSection,
}: RoadmapNodeCardProps) {
  const isTopic = node.kind === "topic";
  const label = `${node.title}${node.subtitle ? `, ${node.subtitle}` : ""}`;

  return (
    <button
      type="button"
      aria-label={label}
      onClick={() => {
        if (node.itemId) onSelectItem(node.itemId);
        if (node.sectionKey) onSelectSection(node.sectionKey);
      }}
      className={cn(
        "absolute flex text-left shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-lg focus:outline-none focus:ring-4 focus:ring-blue-200",
        isTopic
          ? "items-center justify-center rounded-lg border-2 border-slate-950 bg-yellow-300 px-5 text-center font-bold text-slate-950"
          : "items-center gap-3 rounded-2xl border bg-white px-4 text-slate-950",
        node.recommended && "ring-4 ring-blue-200",
        node.status === "completed" && !isTopic && "border-emerald-200 bg-emerald-50",
        node.status === "skipped" && !isTopic && "border-slate-200 bg-slate-100 text-slate-500",
      )}
      style={{
        left: node.x,
        top: node.y,
        width: node.width,
        height: node.height,
      }}
    >
      {!isTopic && (
        <span
          className={cn(
            "flex h-9 w-9 shrink-0 items-center justify-center rounded-full border",
            node.status === "completed" && "border-emerald-600 bg-emerald-600 text-white",
            node.status === "pending" && !node.recommended && "border-slate-300 text-slate-500",
            node.recommended && "border-blue-600 bg-blue-600 text-white",
          )}
        >
          {statusIcon(node.status, node.recommended)}
        </span>
      )}
      <span className="min-w-0">
        <span className={cn("block truncate", isTopic ? "text-base" : "text-sm font-semibold")}>
          {node.title}
        </span>
        {node.subtitle && !isTopic && (
          <span className="mt-1 block text-xs text-slate-500">{node.subtitle}</span>
        )}
      </span>
      {isTopic && <Circle className="ml-2 h-3 w-3 fill-current" aria-hidden="true" />}
    </button>
  );
}
```

- [ ] **Step 6: Implement `RoadmapPlanner`**

Create `frontend/features/learning-path/components/RoadmapPlanner.tsx`:

```tsx
"use client";

import { useMemo } from "react";
import { buildRoadmapModel } from "../roadmap-model";
import type { PathItemResponse } from "@/types";
import RoadmapConnectorLayer from "./RoadmapConnectorLayer";
import RoadmapNodeCard from "./RoadmapNodeCard";

interface RoadmapPlannerProps {
  items: PathItemResponse[];
  onSelectItem: (id: string) => void;
  onSelectSection: (sectionKey: string) => void;
}

export default function RoadmapPlanner({
  items,
  onSelectItem,
  onSelectSection,
}: RoadmapPlannerProps) {
  const model = useMemo(() => buildRoadmapModel(items), [items]);

  if (items.length === 0) {
    return (
      <div className="rounded-3xl border bg-slate-50 p-8 text-center" style={{ borderColor: "var(--border)" }}>
        <p className="text-sm font-semibold text-slate-700">Chưa có lộ trình</p>
        <p className="mt-1 text-sm text-slate-500">Chọn một path cụ thể để planner tạo roadmap.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-3xl border bg-slate-50 p-4" style={{ borderColor: "var(--border)" }}>
      <div
        className="relative mx-auto"
        style={{
          width: model.width,
          height: model.height,
          minWidth: model.width,
        }}
      >
        <RoadmapConnectorLayer
          width={model.width}
          height={model.height}
          connectors={model.connectors}
        />
        {model.nodes.map((node) => (
          <RoadmapNodeCard
            key={node.id}
            node={node}
            onSelectItem={onSelectItem}
            onSelectSection={onSelectSection}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Implement `PlannerHeader`**

Create `frontend/features/learning-path/components/PlannerHeader.tsx`:

```tsx
"use client";

import ViewToggle, { type LearnView } from "./ViewToggle";
import type { LearningProfile } from "../profile";

interface PlannerHeaderProps {
  profile: LearningProfile;
  completedUnits: number;
  totalUnits: number;
  inProgressUnits: number;
  view: LearnView;
  onViewChange: (view: LearnView) => void;
}

export default function PlannerHeader({
  profile,
  completedUnits,
  totalUnits,
  inProgressUnits,
  view,
  onViewChange,
}: PlannerHeaderProps) {
  const percent = totalUnits > 0 ? Math.round((completedUnits / totalUnits) * 100) : 0;

  return (
    <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div>
        <p className="text-sm font-semibold text-blue-600">Planner</p>
        <h1 className="mt-1 text-3xl font-black tracking-tight" style={{ color: "var(--text-primary)" }}>
          {profile.label}
        </h1>
        <p className="mt-2 text-sm" style={{ color: "var(--text-secondary)" }}>
          Start {profile.startCourse ?? "tự chọn"} · {inProgressUnits} bài đang học
        </p>
      </div>
      <div className="flex flex-col gap-3 md:items-end">
        <ViewToggle view={view} onChange={onViewChange} />
        <div className="w-full rounded-2xl border bg-white p-4 md:w-72" style={{ borderColor: "var(--border)" }}>
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-slate-500">Tiến độ tổng thể</span>
            <span className="font-black text-blue-600">{percent}%</span>
          </div>
          <div className="mt-3 h-2 rounded-full bg-slate-200">
            <div className="h-2 rounded-full bg-blue-600" style={{ width: `${percent}%` }} />
          </div>
        </div>
      </div>
    </header>
  );
}
```

- [ ] **Step 8: Run component tests**

Run:

```bash
cd frontend
npm test -- --run tests/unit/learning-path/roadmap-components.test.tsx
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/features/learning-path/components/PlannerHeader.tsx frontend/features/learning-path/components/PathRequiredState.tsx frontend/features/learning-path/components/RoadmapConnectorLayer.tsx frontend/features/learning-path/components/RoadmapNodeCard.tsx frontend/features/learning-path/components/RoadmapPlanner.tsx frontend/tests/unit/learning-path/roadmap-components.test.tsx
git commit -m "feat: add roadmap planner components"
```

## Task 4: Wire Planner Into `/learn`

**Files:**
- Modify: `frontend/features/learning-path/components/LearningPathShell.tsx`
- Modify: `frontend/features/learning-path/components/RoadmapCanvas.tsx`
- Modify: `frontend/features/learning-path/store.ts`

- [ ] **Step 1: Replace `RoadmapCanvas` implementation with custom roadmap renderer**

Modify `frontend/features/learning-path/components/RoadmapCanvas.tsx` to remove ReactFlow usage and delegate to `RoadmapPlanner`:

V1 intentionally trades ReactFlow zoom/pan/minimap for a simpler roadmap-style scroll viewport. Do not claim zoom/pan parity in V1. If product still needs zoom controls after visual QA, add them as a separate task using CSS transform scale on `RoadmapPlanner`.

```tsx
"use client";

import RoadmapPlanner from "./RoadmapPlanner";
import PathRequiredState from "./PathRequiredState";
import { useLearningPathStore } from "../store";

export default function RoadmapCanvas() {
  const items = useLearningPathStore((s) => s.items);
  const profile = useLearningPathStore((s) => s.profile);
  const selectItem = useLearningPathStore((s) => s.selectItem);
  const selectSection = useLearningPathStore((s) => s.selectSection);

  if (!profile || items.length === 0) {
    return <PathRequiredState />;
  }

  return (
    <RoadmapPlanner
      items={items}
      onSelectItem={selectItem}
      onSelectSection={selectSection}
    />
  );
}
```

- [ ] **Step 2: Add nullable selected path profile to the learning path store**

Modify `frontend/features/learning-path/store.ts`:

```ts
import { persist } from "zustand/middleware";
import {
  type LearningProfile,
} from "./profile";
```

Extend `LearningPathState`:

```ts
profile: LearningProfile | null;
setProfile: (profile: LearningProfile | null) => void;
```

Initialize and update:

```ts
profile: null,
setProfile: (profile) => set({ profile }),
```

Wrap the store with `persist` and store only profile-related fields so refresh preserves the selected concrete path:

```ts
export const useLearningPathStore = create<LearningPathState>()(
  persist(
    (set, get) => ({
      // existing state...
      profile: null,
      setProfile: (profile) => set({ profile }),
    }),
    {
      name: "learning-path-profile",
      partialize: (state) => ({
        profile: state.profile,
      }),
    },
  ),
);
```

Do not persist `generatedTopologyHash` in Task 4; that field is introduced in Task 5 with the stale-profile banner.

- [ ] **Step 3: Update `LearningPathShell` header and CTA**

Modify `frontend/features/learning-path/components/LearningPathShell.tsx` imports:

```tsx
import PathRequiredState from "./PathRequiredState";
import PlannerHeader from "./PlannerHeader";
```

Read profile from store:

```tsx
const profile = useLearningPathStore((s) => s.profile);
```

After existing loading/error branches, render `PathRequiredState` before the planner header if no concrete profile/path exists or if the selected profile has no generated items:

```tsx
if (!profile || items.length === 0) {
  return <PathRequiredState />;
}
```

Replace the existing title/header block with:

```tsx
<PlannerHeader
  profile={profile}
  completedUnits={summary?.completed_units ?? 0}
  totalUnits={summary?.total_units ?? items.length}
  inProgressUnits={summary?.in_progress_units ?? 0}
  view={view}
  onViewChange={setView}
/>
```

Keep loading, error, graph/timeline, and drawer branches unchanged. `LearningPathShell` is the source of truth for path-required UX. `RoadmapCanvas` may keep a defensive guard, but normal empty path data should be handled at the shell level before rendering header/canvas.

- [ ] **Step 4: Run focused frontend tests**

Run:

```bash
cd frontend
npm test -- --run tests/unit/learning-path/profile.test.ts tests/unit/learning-path/roadmap-model.test.ts tests/unit/learning-path/roadmap-components.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Run existing learning-path tests**

Run:

```bash
cd frontend
npm test -- --run tests/unit/learning-path
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/features/learning-path/components/LearningPathShell.tsx frontend/features/learning-path/components/RoadmapCanvas.tsx frontend/features/learning-path/store.ts
git commit -m "feat: wire roadmap planner into learn page"
```

## Task 5: Add Profile Change/Stale Path UX Contract

**Files:**
- Modify: `frontend/features/learning-path/profile.ts`
- Create: `frontend/features/learning-path/components/ProfileChangeBanner.tsx`
- Create: `frontend/tests/unit/learning-path/profile-change.test.tsx`
- Modify: `frontend/features/learning-path/components/LearningPathShell.tsx`

- [ ] **Step 1: Write tests for CV -> NLP profile change behavior**

Create `frontend/tests/unit/learning-path/profile-change.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import ProfileChangeBanner from "@/features/learning-path/components/ProfileChangeBanner";
import {
  describeProfileChange,
  isProfilePathStale,
  type LearningProfile,
} from "@/features/learning-path/profile";

const cvProfile: LearningProfile = {
  pathKey: "dl_cv",
  label: "Deep Learning -> Computer Vision",
  startCourse: "CS230",
  selectedCourseIds: ["CS230", "CS231n"],
  weeklyHours: 6,
  source: "onboarding",
  topologyHash: "onboarding:dl_cv:CS230:CS230,CS231n",
  pacingHash: "weekly:6",
  generatedFromProfileHash: "onboarding:dl_cv:CS230:CS230,CS231n",
};

const nlpProfile: LearningProfile = {
  pathKey: "dl_nlp",
  label: "Deep Learning -> NLP",
  startCourse: "CS230",
  selectedCourseIds: ["CS230", "CS224n"],
  weeklyHours: 6,
  source: "onboarding",
  topologyHash: "onboarding:dl_nlp:CS230:CS224n,CS230",
  pacingHash: "weekly:6",
  generatedFromProfileHash: "onboarding:dl_nlp:CS230:CS224n,CS230",
};

describe("profile path changes", () => {
  it("detects a stale path when profile hashes differ", () => {
    expect(isProfilePathStale(cvProfile.topologyHash, nlpProfile)).toBe(true);
  });

  it("describes CV to NLP changes without promising progress deletion", () => {
    expect(describeProfileChange(cvProfile, nlpProfile)).toContain("Computer Vision sang NLP");
  });

  it("renders a safe replan banner", () => {
    render(
      <ProfileChangeBanner
        previousProfile={cvProfile}
        currentProfile={nlpProfile}
      />,
    );

    expect(screen.getByText(/giữ tiến độ/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /đang chờ replan backend/i })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd frontend
npm test -- --run tests/unit/learning-path/profile-change.test.tsx
```

Expected: FAIL because helpers and banner do not exist.

- [ ] **Step 3: Add profile stale helpers**

Modify `frontend/features/learning-path/profile.ts`:

```ts
export function isProfilePathStale(
  generatedTopologyHash: string | null | undefined,
  currentProfile: LearningProfile,
): boolean {
  if (!generatedTopologyHash) return false;
  return generatedTopologyHash !== currentProfile.topologyHash;
}

export function describeProfileChange(
  previousProfile: LearningProfile,
  currentProfile: LearningProfile,
): string {
  if (previousProfile.pathKey === "dl_cv" && currentProfile.pathKey === "dl_nlp") {
    return "Bạn đang đổi lộ trình từ Computer Vision sang NLP.";
  }
  if (previousProfile.pathKey === "dl_nlp" && currentProfile.pathKey === "dl_cv") {
    return "Bạn đang đổi lộ trình từ NLP sang Computer Vision.";
  }
  return `Bạn đang đổi lộ trình từ ${previousProfile.label} sang ${currentProfile.label}.`;
}
```

- [ ] **Step 4: Implement `ProfileChangeBanner`**

Create `frontend/features/learning-path/components/ProfileChangeBanner.tsx`:

```tsx
import { RefreshCw } from "lucide-react";
import type { LearningProfile } from "../profile";
import { describeProfileChange } from "../profile";

interface ProfileChangeBannerProps {
  previousProfile: LearningProfile;
  currentProfile: LearningProfile;
}

export default function ProfileChangeBanner({
  previousProfile,
  currentProfile,
}: ProfileChangeBannerProps) {
  return (
    <section className="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-blue-950">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-semibold">
            {describeProfileChange(previousProfile, currentProfile)}
          </p>
          <p className="mt-1 text-sm text-blue-800">
            Planner sẽ giữ tiến độ các phần đã học. V1 chỉ cảnh báo profile/path lệch; backend replan sẽ xử lý thay nhánh khi endpoint sẵn sàng.
          </p>
        </div>
        <button
          type="button"
          disabled
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-blue-100 px-4 text-sm font-semibold text-blue-700"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          Đang chờ replan backend
        </button>
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Wire the banner behind a store value**

Extend `LearningPathState` in `frontend/features/learning-path/store.ts`:

```ts
generatedTopologyHash: string | null;
previousProfile: LearningProfile | null;
```

Initialize:

```ts
generatedTopologyHash: null,
previousProfile: null,
```

Update `setProfile`:

```ts
setProfile: (profile) =>
  set((state) => ({
    previousProfile: state.profile,
    profile,
  })),
```

In `loadPath`, keep `generatedTopologyHash` as the current topology hash after a successful path load:

```ts
generatedTopologyHash: get().profile?.topologyHash ?? null,
```

Also extend the `persist.partialize` object introduced in Task 4:

```ts
partialize: (state) => ({
  profile: state.profile,
  generatedTopologyHash: state.generatedTopologyHash,
}),
```

Modify `LearningPathShell.tsx` to render the banner only when `profile` and `previousProfile` exist and `isProfilePathStale(generatedTopologyHash, profile)` is true:

```tsx
<ProfileChangeBanner
  previousProfile={previousProfile}
  currentProfile={profile}
/>
```

- [ ] **Step 6: Run profile change tests**

Run:

```bash
cd frontend
npm test -- --run tests/unit/learning-path/profile-change.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/features/learning-path/profile.ts frontend/features/learning-path/components/ProfileChangeBanner.tsx frontend/features/learning-path/components/LearningPathShell.tsx frontend/features/learning-path/store.ts frontend/tests/unit/learning-path/profile-change.test.tsx
git commit -m "feat: prepare planner for profile changes"
```

## Task 6: Link Player Checkpoints, Skip Eligibility, And Planner UX

**Files:**
- Create: `frontend/features/learning-path/player-insights.ts`
- Create: `frontend/features/learning-path/components/PlayerInsightBadge.tsx`
- Create: `frontend/tests/unit/learning-path/player-insights.test.ts`
- Modify: `frontend/features/learning-path/components/RoadmapNodeCard.tsx`
- Modify: `frontend/components/learn/LearningUnitShell.tsx`
- Modify: `frontend/tests/unit/content/inline-video-quiz-overlay.test.tsx`

**Current state to preserve:** Player already has chapter segmentation, checkpoint markers, inline midpoint/end quizzes, session resume, and progress sync. It writes `current_progress.inline_quiz` through `learningSessionApi.updateProgress`, and `quiz_service.complete_quiz` updates mastery and auto-completes the learning unit when the completed quiz is the standalone mini quiz or the end inline quiz. Planner should consume this signal and make the path feel adaptive; it should not add a blind skip button that bypasses the existing checkpoint/quiz flow. Return-user behavior should use existing `planner_session_state`, `learning_progress_records`, and `learner_mastery_kp.updated_at` signals when the API exposes them; do not infer stale mastery from watch progress alone.

- [ ] **Step 1: Write failing tests for player insight derivation**

Create `frontend/tests/unit/learning-path/player-insights.test.ts`:

```ts
import {
  derivePlayerInsight,
  type PlayerProgressSnapshot,
} from "@/features/learning-path/player-insights";

describe("derivePlayerInsight", () => {
  it("suggests resume when a user is mid-video", () => {
    const snapshot: PlayerProgressSnapshot = {
      learning_unit_id: "unit-1",
      watch_percent: 0.62,
      video_finished: false,
      inline_quiz: {},
    };

    expect(derivePlayerInsight(snapshot)).toMatchObject({
      tone: "resume",
      label: "Tiếp tục từ 62%",
    });
  });

  it("surfaces a ready midpoint quiz as the next planner action", () => {
    const snapshot: PlayerProgressSnapshot = {
      learning_unit_id: "unit-1",
      watch_percent: 0.55,
      video_finished: false,
      inline_quiz: {
        midpoint: { shown: false },
      },
    };

    expect(derivePlayerInsight(snapshot)).toMatchObject({
      tone: "quiz_ready",
      label: "Mid-video quiz đã mở",
    });
  });

  it("marks the unit as complete when end quiz is completed", () => {
    const snapshot: PlayerProgressSnapshot = {
      learning_unit_id: "unit-1",
      watch_percent: 0.97,
      video_finished: true,
      inline_quiz: {
        end: { completed_session_id: "session-1" },
      },
    };

    expect(derivePlayerInsight(snapshot)).toMatchObject({
      tone: "complete",
      label: "Đã hoàn tất end quiz",
    });
  });

  it("does not mark end quiz complete from video completion alone", () => {
    const snapshot: PlayerProgressSnapshot = {
      learning_unit_id: "unit-1",
      watch_percent: 1,
      video_finished: true,
      inline_quiz: {},
    };

    expect(derivePlayerInsight(snapshot)).toMatchObject({
      tone: "quiz_ready",
      label: "End quiz đã mở",
      hrefSuffix: "#end-quiz",
    });
  });

  it("surfaces stale mastery as placement-lite instead of blind skip", () => {
    const snapshot: PlayerProgressSnapshot = {
      learning_unit_id: "unit-1",
      watch_percent: 1,
      video_finished: true,
      inline_quiz: {
        end: { completed_session_id: "session-1" },
      },
      mastery_stale: true,
    };

    expect(derivePlayerInsight(snapshot)).toMatchObject({
      tone: "placement_lite",
      label: "Mastery cũ, làm placement-lite",
      hrefSuffix: "#end-quiz",
    });
  });

  it("surfaces review due for returning users", () => {
    const snapshot: PlayerProgressSnapshot = {
      learning_unit_id: "unit-1",
      watch_percent: 1,
      video_finished: true,
      inline_quiz: {
        end: { completed_session_id: "session-1" },
      },
      review_due_count: 3,
    };

    expect(derivePlayerInsight(snapshot)).toMatchObject({
      tone: "review_due",
      label: "Ôn lại 3 KP",
    });
  });
});
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
cd frontend
npm test -- --run tests/unit/learning-path/player-insights.test.ts
```

Expected: FAIL because `player-insights.ts` does not exist.

- [ ] **Step 3: Implement player insight derivation**

Create `frontend/features/learning-path/player-insights.ts`:

```ts
import type { LearningSessionInlineQuizProgress } from "@/types";

export type PlayerInsightTone =
  | "not_started"
  | "resume"
  | "quiz_ready"
  | "quiz_active"
  | "complete"
  | "review_due"
  | "placement_lite";

export interface PlayerProgressSnapshot {
  learning_unit_id: string;
  watch_percent?: number | null;
  video_finished?: boolean | null;
  inline_quiz?: LearningSessionInlineQuizProgress | null;
  has_end_quiz?: boolean | null;
  last_opened_at?: string | null;
  review_due_count?: number | null;
  mastery_stale?: boolean | null;
}

export interface PlayerInsight {
  tone: PlayerInsightTone;
  label: string;
  hrefSuffix: string | null;
}

function checkpointCompleted(
  inlineQuiz: LearningSessionInlineQuizProgress | null | undefined,
  checkpoint: "midpoint" | "end",
): boolean {
  return Boolean(inlineQuiz?.[checkpoint]?.completed_session_id);
}

function checkpointActive(
  inlineQuiz: LearningSessionInlineQuizProgress | null | undefined,
  checkpoint: "midpoint" | "end",
): boolean {
  return Boolean(inlineQuiz?.[checkpoint]?.active_session_id);
}

export function derivePlayerInsight(snapshot: PlayerProgressSnapshot | null): PlayerInsight {
  if (!snapshot) {
    return { tone: "not_started", label: "Chưa bắt đầu", hrefSuffix: null };
  }

  const watchPercent = Math.round((snapshot.watch_percent ?? 0) * 100);
  const inlineQuiz = snapshot.inline_quiz;

  if (snapshot.mastery_stale) {
    return { tone: "placement_lite", label: "Mastery cũ, làm placement-lite", hrefSuffix: "#end-quiz" };
  }

  if ((snapshot.review_due_count ?? 0) > 0) {
    return { tone: "review_due", label: `Ôn lại ${snapshot.review_due_count} KP`, hrefSuffix: null };
  }

  if (checkpointCompleted(inlineQuiz, "end")) {
    return { tone: "complete", label: "Đã hoàn tất end quiz", hrefSuffix: null };
  }

  if (checkpointActive(inlineQuiz, "end")) {
    return { tone: "quiz_active", label: "End quiz đang dở", hrefSuffix: "#end-quiz" };
  }

  if ((snapshot.video_finished || watchPercent >= 95) && snapshot.has_end_quiz !== false) {
    return { tone: "quiz_ready", label: "End quiz đã mở", hrefSuffix: "#end-quiz" };
  }

  if (snapshot.video_finished) {
    return { tone: "complete", label: "Đã xem xong", hrefSuffix: null };
  }

  if (checkpointActive(inlineQuiz, "midpoint")) {
    return { tone: "quiz_active", label: "Mid-video quiz đang dở", hrefSuffix: "#midpoint-quiz" };
  }

  if (watchPercent >= 50 && !checkpointCompleted(inlineQuiz, "midpoint")) {
    return { tone: "quiz_ready", label: "Mid-video quiz đã mở", hrefSuffix: "#midpoint-quiz" };
  }

  if (watchPercent > 0) {
    return { tone: "resume", label: `Tiếp tục từ ${watchPercent}%`, hrefSuffix: null };
  }

  return { tone: "not_started", label: "Chưa bắt đầu", hrefSuffix: null };
}
```

- [ ] **Step 4: Render planner insight badges on roadmap nodes**

Create `frontend/features/learning-path/components/PlayerInsightBadge.tsx`:

```tsx
import { cn } from "@/lib/utils";
import type { PlayerInsight } from "../player-insights";

interface PlayerInsightBadgeProps {
  insight: PlayerInsight;
}

export default function PlayerInsightBadge({ insight }: PlayerInsightBadgeProps) {
  if (insight.tone === "not_started") return null;

  return (
    <span
      className={cn(
        "mt-2 inline-flex w-max rounded-full px-2 py-0.5 text-[11px] font-semibold",
        insight.tone === "resume" && "bg-blue-50 text-blue-700",
        insight.tone === "quiz_ready" && "bg-amber-50 text-amber-700",
        insight.tone === "quiz_active" && "bg-orange-50 text-orange-700",
        insight.tone === "complete" && "bg-emerald-50 text-emerald-700",
        insight.tone === "review_due" && "bg-cyan-50 text-cyan-700",
        insight.tone === "placement_lite" && "bg-rose-50 text-rose-700",
      )}
    >
      {insight.label}
    </span>
  );
}
```

Modify `RoadmapPlanner.tsx` and `RoadmapNodeCard.tsx` so the active/resume unit can show the badge without coupling cards to the Zustand store:

- `RoadmapPlanner` accepts `currentProgress?: PlayerProgressSnapshot | null`.
- `RoadmapPlanner` computes `derivePlayerInsight(currentProgress)` only when `node.item?.learning_unit_id === currentProgress?.learning_unit_id`.
- `RoadmapNodeCard` receives `insight?: PlayerInsight | null`.
- Do not fetch per-node progress in V1 because that would create an N+1 API pattern.

Modify `RoadmapCanvas.tsx` to pass the current progress snapshot into `RoadmapPlanner`. Use the existing store/API field that carries player progress; if the store does not expose it yet, add a nullable `currentProgress` field populated from the learning-path response.

```tsx
const currentProgress = useLearningPathStore((s) => s.currentProgress);

<RoadmapPlanner
  items={items}
  currentProgress={currentProgress}
  onSelectItem={selectItem}
  onSelectSection={selectSection}
/>
```

- [ ] **Step 5: Deep-link checkpoint actions from planner to player**

Modify `LearningUnitShell.tsx` to read `window.location.hash` on mount and on `hashchange`. If hash is `#midpoint-quiz` or `#end-quiz`, scroll to the checkpoint card and open the quiz only when the checkpoint is available or active. Use the existing `startCheckpointQuiz(checkpoint)` function; do not duplicate quiz-start logic.

Add `useRef` to the React imports if it is not already imported.

```tsx
const handledCheckpointHashRef = useRef<string | null>(null);

useEffect(() => {
  if (typeof window === "undefined") return;
  const openCheckpointFromHash = () => {
    const hash = window.location.hash;
    if (handledCheckpointHashRef.current === hash) return;

    const checkpoint =
      hash === "#midpoint-quiz"
        ? "midpoint"
        : hash === "#end-quiz"
          ? "end"
          : null;
    if (!checkpoint) return;

    const status = checkpointStatus.find((entry) => entry.checkpoint === checkpoint);
    if (!status || (!status.active && !status.available)) return;
    handledCheckpointHashRef.current = hash;
    void startCheckpointQuiz(checkpoint);
  };

  openCheckpointFromHash();
  window.addEventListener("hashchange", openCheckpointFromHash);
  return () => window.removeEventListener("hashchange", openCheckpointFromHash);
}, [checkpointStatus, startCheckpointQuiz]);
```

- [ ] **Step 6: Add “skip by verification” UX, not blind skip**

In `LearningUnitShell.tsx`, add a secondary CTA near checkpoint cards:

- If midpoint/end quiz is ready, label it `Làm quiz để rút gọn / xác minh skip`.
- If backend later exposes `can_skip`, this CTA can become `Bỏ qua unit`.
- For V1, do not call `updatePathStatus(..., "skipped")` from player unless the backend says skip is allowed. The existing skip policy requires mastery LCB or latest quiz score, so blind skip creates a frustrating forbidden error.

- [ ] **Step 7: Run insight tests**

Run:

```bash
cd frontend
npm test -- --run tests/unit/learning-path/player-insights.test.ts
```

Expected: PASS.

- [ ] **Step 8: Run existing player tests**

Run:

```bash
cd frontend
npm test -- --run tests/routes/learning tests/unit/content
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/features/learning-path/player-insights.ts frontend/features/learning-path/components/PlayerInsightBadge.tsx frontend/features/learning-path/components/RoadmapNodeCard.tsx frontend/components/learn/LearningUnitShell.tsx frontend/tests/unit/learning-path/player-insights.test.ts frontend/tests/unit/content/inline-video-quiz-overlay.test.tsx
git commit -m "feat: link planner with player checkpoints"
```

## Task 7: Final Verification

**Files:**
- No new files.

- [ ] **Step 1: Run frontend learning-path tests**

Run:

```bash
cd frontend
npm test -- --run tests/unit/learning-path
```

Expected: PASS.

- [ ] **Step 2: Run route-level learn tests**

Run:

```bash
cd frontend
npm test -- --run tests/routes/learning
```

Expected: PASS.

- [ ] **Step 3: Run TypeScript check**

Run:

```bash
cd frontend
npm run type-check
```

Expected: PASS. If the project does not have `type-check`, run:

```bash
cd frontend
npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 4: Run GitNexus detect changes before commit/PR**

Run GitNexus change detection using the available project GitNexus MCP/CLI workflow. The expected affected area is frontend learning-path planner only.

- [ ] **Step 5: Scan generated plan/code snippets for invalid TSX placeholders**

Before implementation handoff or final commit, scan for broken JSX style snippets that can be introduced by markdown copying:

```bash
rg -n "style=\\s+|style=\\s*borderColor|style=\\s*color|left: node\\.x,\\s+top: node\\.y|width: model\\.width,\\s+height: model\\.height" frontend
rg -n "style=\\{\\{[0-9]+\\}\\}" frontend
```

Expected: no invalid `style=` placeholder snippets. Valid React style objects should use explicit object properties, e.g. `style={{ borderColor: "var(--border)" }}`.

- [ ] **Step 6: Final commit**

```bash
git add frontend/features/learning-path frontend/tests/unit/learning-path frontend/types/index.ts
git commit -m "feat: add learn roadmap planner"
```

## Task 8: Enrich Planner With Schema V2 Graph Signals

**Files:**
- Modify: `src/repositories/canonical_content_repo.py`
- Modify: `src/services/recommendation_engine.py`
- Modify: `src/schemas/learning_path.py`
- Modify: `frontend/types/index.ts`
- Create: `frontend/features/learning-path/planner-reasons.ts`
- Modify: `frontend/features/learning-path/roadmap-model.ts`
- Modify: `frontend/features/learning-path/components/RoadmapNodeCard.tsx`
- Create: `tests/services/test_schema_v2_planner_enrichment.py`
- Create: `frontend/tests/unit/learning-path/planner-reasons.test.tsx`

**Current state to improve:** `recommendation_engine.py` already uses selected courses, linked runtime learning units, `unit_kp_map`, and `learner_mastery_kp` to classify `skip | quick_review | deep_practice`. Local schema v2 models and migrations include canonical unit metadata such as `section_flags`, `salience_score`, `content_type`, `is_worth_learning`, `has_quiz_items`, `override_critical_kp`, and `active`, but the planner should not require every row to be fully backfilled. Implement this as **canonical-first with graph-derived fallback**:

- Use canonical unit metadata directly when populated.
- If canonical metadata is missing/null, derive criticality and salience from `unit_kp_map` + `concepts_kp`.
- Derive quiz availability from `question_bank` + `item_phase_map` counts so logistics/reference segments do not receive quiz UX.
- Derive prerequisite gaps from `prerequisite_edges` using at least 2-hop closure.
- Treat `learner_mastery_kp` as evidence-backed only when it has observed assessment items; self-report prior can affect pacing/path choice but not skip/waive/bridge.
- Classify segment policy as `core | reference | hidden` using `content_type`, `section_flags`, `question_bank`, and `item_phase_map`.

This keeps the planner aligned with schema v2 while avoiding a frontend-only plan that silently depends on DB denormalization.

- [ ] **Step 1: Write failing backend enrichment tests**

Create `tests/services/test_schema_v2_planner_enrichment.py` with tests for pure helper functions before touching DB-heavy planner code:

```python
from types import SimpleNamespace

from src.services.recommendation_engine import (
    classify_schema_v2_unit_priority,
    find_prerequisite_gaps,
    is_mastery_evidence_backed,
)


def test_classify_schema_v2_unit_priority_promotes_critical_high_salience_unit():
    unit = SimpleNamespace(
        content_type="concept",
        is_worth_learning=True,
        salience_score="high",
        has_quiz_items=True,
        override_critical_kp=True,
        active=True,
    )

    priority = classify_schema_v2_unit_priority(unit)

    assert priority.required is True
    assert priority.reason_codes == ["critical_kp", "high_salience", "quiz_available"]


def test_classify_schema_v2_unit_priority_demotes_inactive_or_not_worth_learning_unit():
    unit = SimpleNamespace(
        content_type="administrative",
        is_worth_learning=False,
        salience_score="low",
        has_quiz_items=False,
        override_critical_kp=False,
        active=True,
    )

    priority = classify_schema_v2_unit_priority(unit)

    assert priority.required is False
    assert "optional_low_salience" in priority.reason_codes


def test_classify_schema_v2_unit_priority_derives_from_kp_graph_when_unit_fields_missing():
    unit = SimpleNamespace(
        content_type=None,
        is_worth_learning=None,
        salience_score=None,
        has_quiz_items=None,
        override_critical_kp=None,
        active=True,
    )
    unit_kp_rows = [
        SimpleNamespace(
            kp_id="kp_attention",
            planner_role="main",
            coverage_level="dominant",
            coverage_weight=0.9,
        ),
    ]
    kp_by_id = {
        "kp_attention": SimpleNamespace(
            kp_id="kp_attention",
            importance_level="critical",
            structural_role="gateway",
        ),
    }

    priority = classify_schema_v2_unit_priority(
        unit,
        unit_kp_rows=unit_kp_rows,
        kp_by_id=kp_by_id,
        quiz_item_count=2,
    )

    assert priority.required is True
    assert priority.reason_codes == ["critical_kp", "high_salience", "quiz_available"]


def test_find_prerequisite_gaps_detects_two_hop_missing_source_kp_before_target():
    gaps = find_prerequisite_gaps(
        target_kp_ids=["kp_transformers"],
        prerequisite_edges=[
            SimpleNamespace(source_kp_id="kp_attention", target_kp_id="kp_transformers", active=True),
            SimpleNamespace(source_kp_id="kp_linear_algebra", target_kp_id="kp_attention", active=True),
            SimpleNamespace(source_kp_id="kp_python", target_kp_id="kp_unrelated", active=True),
        ],
        mastered_kp_ids={"kp_python"},
        max_depth=2,
    )

    assert gaps == ["kp_attention", "kp_linear_algebra"]


def test_self_report_prior_is_not_evidence_backed_mastery():
    mastery = SimpleNamespace(
        n_items_observed=0,
        updated_by="self_report_prior",
    )

    assert is_mastery_evidence_backed(mastery) is False


def test_assessment_items_are_evidence_backed_mastery():
    mastery = SimpleNamespace(
        n_items_observed=3,
        updated_by="mini_quiz",
    )

    assert is_mastery_evidence_backed(mastery) is True


def test_logistics_unit_is_hidden_even_if_active():
    unit = SimpleNamespace(
        content_type="administrative",
        section_flags=["logistics"],
        is_worth_learning=True,
        salience_score="low",
        has_quiz_items=False,
        override_critical_kp=False,
        active=True,
    )

    priority = classify_schema_v2_unit_priority(unit)

    assert priority.required is False
    assert priority.segment_policy == "hidden"
    assert "hidden_logistics" in priority.reason_codes


def test_reference_unit_is_optional_summary_not_core_quiz():
    unit = SimpleNamespace(
        content_type="reference",
        section_flags=["reference"],
        is_worth_learning=True,
        salience_score="medium",
        has_quiz_items=False,
        override_critical_kp=False,
        active=True,
    )

    priority = classify_schema_v2_unit_priority(unit)

    assert priority.required is False
    assert priority.segment_policy == "reference"
    assert "reference_only" in priority.reason_codes
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/services/test_schema_v2_planner_enrichment.py -q
```

Expected: FAIL because the helper functions do not exist.

- [ ] **Step 3: Add canonical unit metadata repository method**

Modify `src/repositories/canonical_content_repo.py`:

```python
from sqlalchemy import func, select

from src.models.canonical import CanonicalUnit, ConceptKP, ItemPhaseMap, PrerequisiteEdge, QuestionBankItem, UnitKPMap
```

Add:

```python
async def get_canonical_units_by_ids(self, canonical_unit_ids: list[str]) -> dict[str, CanonicalUnit]:
    if not canonical_unit_ids:
        return {}
    result = await self.session.execute(
        select(CanonicalUnit).where(CanonicalUnit.unit_id.in_(canonical_unit_ids))
    )
    return {unit.unit_id: unit for unit in result.scalars().all()}


async def get_concepts_by_ids(self, kp_ids: list[str]) -> dict[str, ConceptKP]:
    if not kp_ids:
        return {}
    result = await self.session.execute(
        select(ConceptKP).where(ConceptKP.kp_id.in_(kp_ids))
    )
    return {kp.kp_id: kp for kp in result.scalars().all()}


async def get_quiz_item_counts_by_unit_ids(
    self,
    unit_ids: list[str],
    *,
    phases: tuple[str, ...] = (
        "placement",
        "mini_quiz",
        "skip_verification",
        "bridge_check",
        "final_quiz",
        "review",
    ),
) -> dict[str, int]:
    if not unit_ids:
        return {}
    result = await self.session.execute(
        select(QuestionBankItem.unit_id, func.count(func.distinct(QuestionBankItem.item_id)))
        .join(ItemPhaseMap, ItemPhaseMap.item_id == QuestionBankItem.item_id)
        .where(QuestionBankItem.unit_id.in_(unit_ids))
        .where(ItemPhaseMap.phase.in_(phases))
        .group_by(QuestionBankItem.unit_id)
    )
    return {str(unit_id): int(count) for unit_id, count in result.all()}
```

- [ ] **Step 4: Add schema v2 helper functions**

Modify `src/services/recommendation_engine.py`:

```python
from dataclasses import dataclass
```

Add near the classification helpers:

```python
@dataclass(frozen=True)
class SchemaV2UnitPriority:
    required: bool
    reason_codes: list[str]
    priority_bonus: float
    segment_policy: str


@dataclass(frozen=True)
class _FallbackCanonicalUnit:
    active: bool = True


def _salience_to_float(value: str | None) -> float:
    if value is None:
        return 0.5
    normalized = str(value).strip().lower()
    if normalized in {"high", "critical", "core"}:
        return 1.0
    if normalized in {"medium", "med"}:
        return 0.6
    if normalized in {"low", "optional"}:
        return 0.2
    try:
        return max(0.0, min(1.0, float(normalized)))
    except ValueError:
        return 0.5


_IMPORTANCE_WEIGHT = {
    "critical": 1.0,
    "high": 0.8,
    "medium": 0.5,
    "low": 0.2,
}


def _derived_salience_from_kps(unit_kp_rows, kp_by_id: dict[str, object]) -> float:
    if not unit_kp_rows:
        return 0.5
    scores: list[float] = []
    for row in unit_kp_rows:
        kp = kp_by_id.get(str(getattr(row, "kp_id", "")))
        importance = str(getattr(kp, "importance_level", "") or "").lower()
        weight = float(getattr(row, "coverage_weight", 1.0) or 1.0)
        scores.append(_IMPORTANCE_WEIGHT.get(importance, 0.4) * weight)
    if not scores:
        return 0.5
    return max(0.0, min(1.0, max(scores)))


def _has_critical_gateway_kp(unit_kp_rows, kp_by_id: dict[str, object]) -> bool:
    for row in unit_kp_rows or []:
        kp = kp_by_id.get(str(getattr(row, "kp_id", "")))
        importance = str(getattr(kp, "importance_level", "") or "").lower()
        structural_role = str(getattr(kp, "structural_role", "") or "").lower()
        planner_role = str(getattr(row, "planner_role", "") or "").lower()
        coverage_level = str(getattr(row, "coverage_level", "") or "").lower()
        if (
            importance == "critical"
            and structural_role == "gateway"
            and planner_role in {"", "main", "prereq"}
            and coverage_level != "mention"
        ):
            return True
    return False


def _normalized_section_flags(unit) -> set[str]:
    flags = getattr(unit, "section_flags", None) or []
    normalized: set[str] = set()
    for flag in flags:
        if isinstance(flag, str):
            normalized.add(flag.strip().lower())
        elif isinstance(flag, dict):
            for value in flag.values():
                if isinstance(value, str):
                    normalized.add(value.strip().lower())
    return normalized


def classify_segment_policy(unit, *, has_quiz_items: bool, critical: bool, salience: float) -> str:
    content_type = str(getattr(unit, "content_type", "") or "").lower()
    flags = _normalized_section_flags(unit)

    if content_type in {"administrative", "admin", "logistics"} or flags & {"admin", "administrative", "logistics"}:
        return "hidden"
    if content_type in {"reference", "appendix"} or flags & {"reference", "appendix"}:
        return "reference"
    if critical or salience >= 0.8 or has_quiz_items:
        return "core"
    return "core"


def is_mastery_evidence_backed(mastery) -> bool:
    if mastery is None:
        return False
    if int(getattr(mastery, "n_items_observed", 0) or 0) <= 0:
        return False
    updated_by = str(getattr(mastery, "updated_by", "") or "").lower()
    return updated_by not in {"self_report", "self_report_prior", "onboarding_prior"}


def classify_schema_v2_unit_priority(
    unit,
    *,
    unit_kp_rows=None,
    kp_by_id: dict[str, object] | None = None,
    quiz_item_count: int = 0,
) -> SchemaV2UnitPriority:
    kp_by_id = kp_by_id or {}
    reason_codes: list[str] = []
    explicit_salience = getattr(unit, "salience_score", None)
    salience = (
        _salience_to_float(explicit_salience)
        if explicit_salience is not None
        else _derived_salience_from_kps(unit_kp_rows, kp_by_id)
    )
    content_type = str(getattr(unit, "content_type", "") or "").lower()
    is_worth_learning = getattr(unit, "is_worth_learning", None)
    explicit_quiz = getattr(unit, "has_quiz_items", None)
    has_quiz_items = bool(explicit_quiz) if explicit_quiz is not None else quiz_item_count > 0
    critical = bool(getattr(unit, "override_critical_kp", False)) or _has_critical_gateway_kp(unit_kp_rows, kp_by_id)
    active_value = getattr(unit, "active", True)
    active = True if active_value is None else bool(active_value)
    segment_policy = classify_segment_policy(
        unit,
        has_quiz_items=has_quiz_items,
        critical=critical,
        salience=salience,
    )

    if not active:
        return SchemaV2UnitPriority(required=False, reason_codes=["inactive"], priority_bonus=-10.0, segment_policy="hidden")
    if segment_policy == "hidden":
        return SchemaV2UnitPriority(required=False, reason_codes=["hidden_logistics"], priority_bonus=-10.0, segment_policy="hidden")
    if segment_policy == "reference":
        return SchemaV2UnitPriority(required=False, reason_codes=["reference_only"], priority_bonus=-1.0, segment_policy="reference")
    if critical:
        reason_codes.append("critical_kp")
    if salience >= 0.8:
        reason_codes.append("high_salience")
    if has_quiz_items:
        reason_codes.append("quiz_available")
    if is_worth_learning is False and not critical:
        reason_codes.append("optional_low_salience")
    if content_type in {"prerequisite", "foundation"}:
        reason_codes.append("required_prerequisite")

    required = critical or salience >= 0.8 or content_type in {"prerequisite", "foundation"}
    if is_worth_learning is False and not critical:
        required = False

    priority_bonus = (1.0 if required else 0.0) + salience + (0.2 if has_quiz_items else 0.0)
    return SchemaV2UnitPriority(
        required=required,
        reason_codes=reason_codes,
        priority_bonus=priority_bonus,
        segment_policy=segment_policy,
    )


def find_prerequisite_gaps(
    *,
    target_kp_ids: list[str],
    prerequisite_edges,
    mastered_kp_ids: set[str],
    max_depth: int = 2,
) -> list[str]:
    incoming_by_target: dict[str, list[str]] = {}
    for edge in prerequisite_edges:
        if not bool(getattr(edge, "active", True)):
            continue
        source_kp_id = str(getattr(edge, "source_kp_id"))
        target_kp_id = str(getattr(edge, "target_kp_id"))
        incoming_by_target.setdefault(target_kp_id, []).append(source_kp_id)

    frontier = set(target_kp_ids)
    gaps: set[str] = set()
    visited: set[str] = set()

    for _ in range(max_depth):
        next_frontier: set[str] = set()
        for target_kp_id in frontier:
            for source_kp_id in incoming_by_target.get(target_kp_id, []):
                if source_kp_id in visited:
                    continue
                visited.add(source_kp_id)
                if source_kp_id not in mastered_kp_ids:
                    gaps.add(source_kp_id)
                    next_frontier.add(source_kp_id)
        frontier = next_frontier
        if not frontier:
            break

    return sorted(gaps)
```

- [ ] **Step 5: Use canonical metadata and prerequisite gaps in path generation**

In `_generate_canonical_learning_path()`:

1. Load canonical metadata:

```python
canonical_unit_by_id = await content_repo.get_canonical_units_by_ids(canonical_unit_ids)
quiz_counts_by_unit_id = await content_repo.get_quiz_item_counts_by_unit_ids(canonical_unit_ids)
```

2. Load KP metadata and prerequisite edges:

```python
kp_by_id = await content_repo.get_concepts_by_ids(kp_ids)
prerequisite_edges = await content_repo.get_prerequisite_edges_for_kps(kp_ids)
```

3. Derive mastered KP ids:

```python
mastered_kp_ids = {
    kp_id
    for kp_id, row in mastery_by_kp.items()
    if is_mastery_evidence_backed(row)
    and estimate_mastery_lcb_on_read(row, now=generated_at) >= 0.8
}
```

Self-report or onboarding priors should remain available for pacing copy, but must not populate `mastered_kp_ids`.

4. For each unit, compute:

```python
canonical_unit = canonical_unit_by_id.get(unit.canonical_unit_id)
unit_kp_rows = unit_kp_rows_by_unit_id.get(unit.canonical_unit_id, [])
schema_priority = classify_schema_v2_unit_priority(
    canonical_unit or _FallbackCanonicalUnit(),
    unit_kp_rows=unit_kp_rows,
    kp_by_id=kp_by_id,
    quiz_item_count=quiz_counts_by_unit_id.get(unit.canonical_unit_id, 0),
)
prereq_gaps = find_prerequisite_gaps(
    target_kp_ids=unit_kps,
    prerequisite_edges=prerequisite_edges,
    mastered_kp_ids=mastered_kp_ids,
    max_depth=2,
)
```

5. Change action classification. `PathAction.remediate` exists in the current backend/frontend enum; if the enum changes before implementation, keep prerequisite gaps on the strongest existing action and preserve `required_prerequisite` in `reason_codes`. Hidden segment `skip` below is a display exclusion only, not learner skip/waive evidence, and must not create a `WaivedUnit` or mark user progress as skipped.

```python
if prereq_gaps:
    action = PathAction.remediate
elif schema_priority and schema_priority.segment_policy == "hidden":
    action = PathAction.skip
elif schema_priority and schema_priority.segment_policy == "reference":
    action = PathAction.quick_review
elif schema_priority and not schema_priority.required and mastery_lcb >= 0.5:
    action = PathAction.quick_review
else:
    action = PathAction(classify_unit_action(mastery_lcb))
```

6. Store richer rationale in `recommended_path_json`:

```python
"reason_codes": schema_priority.reason_codes if schema_priority else [],
"prerequisite_gap_kp_ids": prereq_gaps,
"segment_policy": schema_priority.segment_policy if schema_priority else "core",
"content_type": getattr(canonical_unit, "content_type", None) if canonical_unit else None,
"salience_score": getattr(canonical_unit, "salience_score", None) if canonical_unit else None,
"has_quiz_items": (
    bool(getattr(canonical_unit, "has_quiz_items", False))
    if canonical_unit and getattr(canonical_unit, "has_quiz_items", None) is not None
    else quiz_counts_by_unit_id.get(unit.canonical_unit_id, 0) > 0
),
"is_worth_learning": getattr(canonical_unit, "is_worth_learning", None) if canonical_unit else None,
"override_critical_kp": bool(getattr(canonical_unit, "override_critical_kp", False)) if canonical_unit else False,
```

- [ ] **Step 6: Extend API response with planner reasons**

Modify `src/schemas/learning_path.py`:

```python
class PlannerUnitReason(BaseModel):
    reason_code: str
    label: str
    details: str
```

Add to `PathItemResponse`:

```python
reason_codes: list[str] = Field(default_factory=list)
prerequisite_gap_kp_ids: list[str] = Field(default_factory=list)
segment_policy: str = "core"
content_type: str | None = None
salience_score: str | None = None
has_quiz_items: bool = False
is_worth_learning: bool | None = None
override_critical_kp: bool = False
```

Modify `_get_canonical_learning_path_rows()` so row includes these fields from `recommended_path_json`.

- [ ] **Step 7: Surface planner reasons in roadmap UI**

Modify `frontend/types/index.ts` `PathItemResponse`:

```ts
reason_codes?: string[];
prerequisite_gap_kp_ids?: string[];
segment_policy?: "core" | "reference" | "hidden";
content_type?: string | null;
salience_score?: string | null;
has_quiz_items?: boolean;
is_worth_learning?: boolean | null;
override_critical_kp?: boolean;
```

Create `frontend/features/learning-path/planner-reasons.ts`:

```ts
export type PlannerReasonCode =
  | "critical_kp"
  | "high_salience"
  | "quiz_available"
  | "optional_low_salience"
  | "required_prerequisite"
  | "quick_review"
  | "skip_by_mastery"
  | "inactive"
  | "reference_only"
  | "hidden_logistics"
  | "mastery_stale"
  | "evidence_required"
  | "review_due";

export function describePlannerReason(code: string): { label: string; details: string } {
  switch (code) {
    case "critical_kp":
      return { label: "Critical KP", details: "Nút này phủ knowledge point trọng yếu." };
    case "high_salience":
      return { label: "High salience", details: "Nội dung có độ ưu tiên cao trong graph." };
    case "quiz_available":
      return { label: "Có quiz", details: "Có câu hỏi để xác minh mastery." };
    case "required_prerequisite":
      return { label: "Prerequisite", details: "Nên học trước các phần phụ thuộc." };
    case "optional_low_salience":
      return { label: "Optional", details: "Có thể rút gọn nếu đã đủ nền tảng." };
    case "quick_review":
      return { label: "Quick review", details: "Chỉ cần ôn nhanh vì mastery khá ổn." };
    case "skip_by_mastery":
      return { label: "Skip by mastery", details: "Có evidence đủ mạnh để bỏ qua." };
    case "inactive":
      return { label: "Inactive", details: "Không nên đưa vào lộ trình mới." };
    case "reference_only":
      return { label: "Reference", details: "Chỉ cần đọc/tóm tắt, không đưa vào quiz core." };
    case "hidden_logistics":
      return { label: "Hidden", details: "Logistics/admin bị ẩn khỏi path chính." };
    case "mastery_stale":
      return { label: "Mastery stale", details: "Nên làm placement-lite trước khi skip." };
    case "evidence_required":
      return { label: "Cần evidence", details: "Self-report không đủ để skip hoặc waive." };
    case "review_due":
      return { label: "Review due", details: "Mastery cũ/yếu, nên ôn lại." };
    default:
      return { label: code, details: "Planner reason chưa có mô tả." };
  }
}
```

Create `frontend/tests/unit/learning-path/planner-reasons.test.tsx`:

```tsx
import { describePlannerReason } from "@/features/learning-path/planner-reasons";

describe("describePlannerReason", () => {
  it("maps known reason codes to UX labels", () => {
    expect(describePlannerReason("critical_kp").label).toBe("Critical KP");
    expect(describePlannerReason("quiz_available").label).toBe("Có quiz");
  });

  it("falls back safely for unknown reason codes", () => {
    expect(describePlannerReason("future_reason")).toEqual({
      label: "future_reason",
      details: "Planner reason chưa có mô tả.",
    });
  });
});
```

Modify `RoadmapNodeCard.tsx` to show compact chips:

```tsx
{node.item?.segment_policy === "reference" ? <span>Reference</span> : null}
{node.item?.reason_codes?.slice(0, 2).map((code) => {
  const reason = describePlannerReason(code);
  return <span key={code} title={reason.details}>{reason.label}</span>;
})}
{node.item?.prerequisite_gap_kp_ids?.length ? <span>Cần bridge</span> : null}
{node.item?.segment_policy === "core" && node.item?.has_quiz_items && !node.item.reason_codes?.includes("quiz_available") ? <span>Có quiz</span> : null}
```

Modify `roadmap-model.ts` after `PathItemResponse.segment_policy` exists:

```ts
const visibleItems = items.filter((item) => item.segment_policy !== "hidden");
const ordered = sortByOrder(visibleItems);
```

Hidden logistics/admin units should be filtered out before `RoadmapNodeCard` renders. If a hidden unit is still present in API data for auditability, `buildRoadmapModel()` must omit it from `nodes` while preserving backend rationale in the row.

- [ ] **Step 8: Run backend planner enrichment tests**

Run:

```bash
uv run pytest tests/services/test_schema_v2_planner_enrichment.py -q
```

Expected: PASS.

- [ ] **Step 9: Run frontend planner reason tests**

Run:

```bash
cd frontend
npm test -- --run tests/unit/learning-path/planner-reasons.test.tsx
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add src/repositories/canonical_content_repo.py src/services/recommendation_engine.py src/schemas/learning_path.py frontend/types/index.ts frontend/features/learning-path frontend/tests/unit/learning-path tests/services/test_schema_v2_planner_enrichment.py
git commit -m "feat: enrich planner with schema v2 graph signals"
```

## Onboarding Handoff Contract

When teammate finishes onboarding, they should not edit roadmap renderer internals. They should only:

1. Import `onboardingToLearningProfile` from `frontend/features/learning-path/profile.ts`.
2. Convert onboarding result to `LearningProfile` using exactly one `selected_path_key`: `dl_cv` or `dl_nlp`.
3. Persist the profile server-side or set it in `useLearningPathStore().setProfile(profile)` before redirecting to `/learn`.
4. Redirect to `/learn`.

Expected flow:

```txt
onboarding form result
  -> validate exactly one selected path: dl_cv or dl_nlp
  -> onboardingToLearningProfile(result)
  -> save profile or update learning-path store
  -> redirect /learn
  -> planner loads/renders the concrete path
```

If onboarding tries to send both CV and NLP, reject the input before calling `onboardingToLearningProfile`. V1 must not synthesize a combined path.

If user changes from CV to NLP:

```txt
old profile hash != new profile hash
  -> show ProfileChangeBanner
  -> user reloads path
  -> existing completed progress remains historical state
  -> backend replan endpoint can archive irrelevant pending CV units and insert NLP units when that scoped feature is implemented
```

## Follow-Up Backend Plan Boundary

Planner V1 intentionally does not implement backend replan. A separate backend plan should add:

- `POST /api/learning-path/replan`
- Request body: `LearningProfile`
- Behavior: preserve completed items, archive no-longer-relevant pending items, insert new pending items, write `plan_history`
- Response body: `LearningPathResponse` plus `generated_from_profile_hash`
- Assessor hardening: ensure placement, mini quiz, skip quiz, and review sessions all write canonical `interactions` and update `learner_mastery_kp` with non-self-report `updated_by`.
- Return-user backend: expose resume/review signals from `planner_session_state`, `learning_progress_records`, and `learner_mastery_kp.updated_at` so the frontend does not infer stale mastery locally.
- Placement-lite backend: when mastery is stale after 7/30 days, expose a lightweight assessment action before allowing skip/waive decisions.

That backend work should be a separate plan because it touches planner service, persistence semantics, and progress history.

## Self-Review

- Spec coverage: `/learn` planner, onboarding/path-selection-as-input-provider, no-default path behavior, CV/NLP-only V1 path constraint, CV/NLP profile change handling, evidence-backed mastery gates, return-user prompts, content segment policy, roadmap.sh-inspired renderer, and tests are covered.
- Placeholder scan: no implementation step depends on an undefined UI component or helper; follow-up backend scope is explicitly outside V1.
- Type consistency: `LearningProfile`, `RoadmapModel`, and `PathItemResponse` names are consistent across tasks.
