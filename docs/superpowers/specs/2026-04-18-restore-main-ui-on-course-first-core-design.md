# Restore Main UI On Course-First Core

> **Historical spec:** This document is preserved for implementation history only. Use `README.md` and `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md` as the active production contract.

## Context

The current `001-course-first-refactor` branch has already moved the product to a course-first experience:

- `Home -> Course Overview -> Start -> auth/onboarding/assessment -> learning unit -> AI Tutor in-context`
- `Course -> Section -> LearningUnit -> Asset` is the active domain model
- `CS231n` is learnable and `CS224n` is `coming_soon`
- `/tutor` is now compatibility behavior, not the primary product entry

That logic should stay in place. The regression from the user's point of view is visual: the branch drifted away from the original UI language on `main`, while the preferred direction is to keep the refactored core but restore the original look and feel with only small layout adjustments.

## Goal

Reapply the visual language from `main` across the current course-first flow without rolling back the new core architecture.

The target outcome is:

- keep the current course-first logic and routing
- restore the familiar visual shell from `main`
- introduce a new `Overview` page that feels native to the original UI
- make the updated experience look like a continuation of `main`, not a redesign

## Non-Goals

- Do not restore the old auth-first redirect behavior from `main`
- Do not bring back `/tutor` as a standalone primary page
- Do not replace the presenter/store/api/gate refactor with UI-coupled logic
- Do not redesign the platform around a new style system

## Source Of Truth

### Behavior source

The current branch remains the source of truth for:

- route flow
- auth and skill-test gating
- course availability states
- presenter/view-model logic
- API contracts
- compatibility redirects

### Presentation source

The `main` branch becomes the source of truth for:

- visual tone
- navigation chrome
- typography choices already present there
- card treatment
- spacing rhythm
- CTA styling
- shared page shell

## Design Direction

Use `main` as a presentation donor and the current branch as a behavior donor.

This means UI components can be reskinned or partially restored from `main`, but their data and interactions must be fed by the current presenter/store/router layer. The refactor stays headless at the core, while the rendered shell moves back toward the original interface.

The visual standard is:

- near-original `main` appearance
- only minor layout adjustments where the old design has no matching page, especially `Course Overview` and the current learning route
- no obvious “new design system” competing with the original look

## Page Strategy

### Home

Restore the overall visual language from `main`, but keep the public course-catalog behavior from the refactor.

Requirements:

- public landing page, not auth-first redirect
- full course catalog rendered through the current catalog state/presenter layer
- recommended vs all courses logic preserved
- tabs only shown when the current logic says they should be shown
- cards and surrounding layout should look like the original home as closely as possible

### Course Overview

This is the only truly new page and should be treated as an extension of the original interface.

Requirements:

- reuse the same nav, spacing, card language, and visual tone as restored home
- present mock overview data cleanly without inventing a separate visual language
- `CS231n` shows a usable start CTA
- `CS224n` shows `coming_soon` state consistently
- avoid over-design; it should feel like a natural missing page from `main`

### Learning Unit

Keep the current route and behavior, but reduce the stylistic gap between the learning page and the restored `main` shell.

Requirements:

- preserve the in-context AI Tutor behavior
- preserve learning-unit routing and gating behavior
- re-skin containers, spacing, navigation chrome, and surrounding layout toward `main`
- do not destabilize player/tutor interactions just to force a pixel-perfect copy

## Component Architecture

The restoration should follow adapter boundaries instead of rollback.

### Keep unchanged

- presenters and view-model builders
- stores
- API modules
- auth redirect helpers
- course gate logic
- runtime compatibility redirects

### Rework

- page-level shells
- shared nav/chrome components
- course card and catalog presentation
- overview presentation components
- learning-page presentation shell

### Adapter rule

When reusing or re-creating `main` UI:

- keep the visual markup/style patterns
- replace any embedded legacy logic with props from the new core
- do not let restored components fetch or decide business state on their own if a presenter already owns that decision

## Implementation Phases

### Phase 1: Restore shared visual shell

- recover shared visual tokens and shell patterns from `main`
- restore navigation, general page chrome, and common surface/card language
- apply the shell to `Home` and `Overview` first

### Phase 2: Adapt course pages to the restored look

- re-skin course catalog, hero area, tabs, and course cards
- build `Overview` with the restored visual vocabulary
- verify `CS231n` and `CS224n` CTA behavior stays correct

### Phase 3: Re-skin learning shell

- align the learning page with the restored visual system as far as safely possible
- keep current behavior and tutor interactions intact
- clean up any remaining visual mismatch with the rest of the platform

## Testing

Each phase should preserve the refactored behavior.

Required verification:

- frontend route/unit tests covering catalog, start flow, personalized catalog, redirects, and learning unit
- typecheck for frontend
- e2e smoke coverage for the public course flow when feasible
- manual visual review against `main` for layout fidelity

## Risks

### Risk: accidental rollback of product logic

Mitigation:

- treat `main` as presentation-only reference
- do not copy old route or auth behavior back into active pages

### Risk: mixed UI from two systems

Mitigation:

- restore shared shell first
- use one visual vocabulary for `Home`, `Overview`, and `Learning`

### Risk: overview page feels bolted on

Mitigation:

- make `Overview` inherit the same layout primitives and CTA patterns as restored `Home`
- avoid introducing new colors, typography, or ornamental patterns

## Success Criteria

The work is successful when:

- the app still follows the refactored course-first flow
- the primary UI feels visually consistent with `main`
- `Overview` looks like part of the original product rather than a redesign
- future UI changes can still target presentational components without rewriting business flow
