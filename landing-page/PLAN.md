# Landing Page Build Plan

## Goal

Build a public landing page at `/` that:

- introduces the product clearly
- explains who the product is for
- persuades visitors to sign up or log in
- stays focused on helping learners improve AI/ML/CV/NLP skills

This page will replace the current catalog-first homepage for unauthenticated visitors.

## Product Positioning

The product is an AI learning platform for people who want:

- a clearer path into AI/ML/CV/NLP
- personalized learning direction instead of random course hopping
- active support while studying, not just a static content library

Primary audiences:

- beginners who need structure
- students or self-learners who know some basics and want a better roadmap
- working technical learners who want to level up into AI-related skills

Tone:

- practical
- outcome-oriented
- serious and credible
- clearly AI-focused, not generic edtech

## Chosen UX Direction

Recommended direction: hybrid scroll storytelling

- desktop: large poster-like sections with light snap behavior
- mobile: natural vertical scrolling without hard snap
- each section should deliver one clear message

Why:

- stronger storytelling than a standard long marketing page
- safer than hard full-screen snapping
- fits an education product better than a presentation-style site

## Routing Decisions

These decisions are now fixed for implementation.

### Root behavior

- unauthenticated `GET /` -> public landing page
- authenticated `GET /` -> keep public landing page for this phase

Reason:

- avoids route churn while the new landing page is introduced
- keeps implementation smaller for the first landing-page PR
- avoids forcing immediate migration of catalog behavior for signed-in users

### Catalog behavior

- current catalog content will be removed from the root homepage in this phase
- moving catalog to a dedicated `/courses` route is explicitly deferred

Reason:

- catalog migration is valid follow-up work, but it is separate from landing-page delivery
- avoids coupling this PR to course route restructuring

### Auth CTA behavior

- primary CTA -> `/register`
- secondary CTA -> `/login`
- no protected page links in public navigation

## Public Navigation Decision

This is now fixed:

- create a dedicated `PublicTopNav` component
- do not reuse the current authenticated `TopNav` for the landing page

Public navigation items:

- `Sản phẩm` -> `#product`
- `Lộ trình học` -> `#roadmap`
- `AI Tutor` -> `#tutor`
- `Liên hệ` -> `#contact`
- `Đăng nhập` -> `/login`
- `Đăng ký` -> `/register`

Reason:

- avoids bounce-to-login behavior from protected routes
- avoids confusing first-time visitors with app navigation
- keeps public and authenticated information architecture intentionally separate

## Approach Options

### Option A: Minimal SaaS landing page

Structure:

- hero
- benefits grid
- feature blocks
- CTA
- footer

Pros:

- fast to build
- low UX risk
- easy to maintain

Cons:

- too generic
- weak product personality
- does not match the poster-style idea

### Option B: Poster-style storytelling page

Structure:

- full-height hero
- full-height feature posters
- strong visual transitions
- CTA close
- team/contact footer

Pros:

- memorable
- strong visual identity
- fits the story-while-scrolling concept

Cons:

- can become too theatrical
- easier to hurt readability
- riskier on mobile

### Option C: Hybrid poster storytelling

Structure:

- strong hero
- 2 to 3 large feature sections
- one dedicated conversion section
- simple footer with team/contact

Pros:

- balances clarity and visual impact
- supports practical product messaging
- works better across desktop and mobile

Cons:

- requires tighter visual discipline
- needs stronger section hierarchy than a normal landing page

## Recommendation

Choose Option C.

This gives the product a more intentional AI-forward public face without turning the page into a gimmick.

## Page Architecture

### Section 1: Hero / Product Introduction

Anchor:

- `#product`

Purpose:

- explain what the product is in one screen
- anchor the message in AI/ML/CV/NLP learning
- give users a clear next step

Core message:

- learn AI/ML/CV/NLP with a guided path, practical structure, and built-in learning support

Suggested content:

- headline
- short supporting paragraph
- primary CTA: `Đăng ký ngay`
- secondary CTA: `Đã có tài khoản? Đăng nhập`
- compact product visual suggesting roadmap + study support

### Section 2: Personalized Learning Path

Anchor:

- `#roadmap`

Purpose:

- explain why the product is not just a catalog
- show how the system adapts to goals and current level

Core message:

- the platform helps learners avoid random study by building a clearer path

Suggested content:

- goal selection
- level-aware guidance
- structured progression across AI/ML/CV/NLP topics
- roadmap-style product panels

### Section 3: AI Chatbot Learning Support

Anchor:

- `#tutor`

Purpose:

- show the interactive support advantage
- explain how the chatbot helps during study, not as a vague AI gimmick

Core message:

- learners can ask, clarify, and continue moving when stuck

Suggested content:

- ask questions while learning
- clarify concepts
- stay in study flow instead of leaving the platform to search elsewhere
- visual motif: conversation panel paired with lesson context

### Section 4: Conversion Section

Purpose:

- remove ambiguity
- give the visitor a clear call to start

Core message:

- if you want a more guided way to build AI skills, start now

Suggested content:

- short outcome-focused summary
- primary CTA: `Đăng ký ngay`
- secondary CTA: `Đăng nhập`

### Section 5: Footer / Team / Contact

Anchor:

- `#contact`

Purpose:

- provide legitimacy and contact information
- close the page cleanly

Suggested content:

- short team introduction
- email
- repo or social links if available
- optional short project status line

## Visual Direction

Chosen style:

- modern AI product look
- stronger than current auth pages
- still readable and credible for an education platform

## Design Tokens

These are implementation anchors, not final branding law, but they are specific enough to reduce ambiguity.

### Color direction

- base page surface: `slate-50` to `white`
- primary deep surface: `slate-950`
- primary text: `slate-950`
- secondary text: `slate-600`
- muted text: `slate-400` or `slate-500`
- accent family: `indigo / cyan / teal`

### Primary gradient

- `from-indigo-600 via-cyan-500 to-teal-400`

### Usage rules

- deep dark section allowed for the chatbot section only
- purple should not be a primary brand color on this page
- avoid more than 2 major card treatments across the entire landing page
- keep bright surfaces as the default and use gradients as accents, not as full-page noise

### Motion rules

- animation should support reading order
- no looping decorative motion that competes with content
- `prefers-reduced-motion` must disable parallax and staggered reveals

## Motion and Scroll Behavior

Desktop:

- use `scroll-snap-type: y proximity`
- use snap only on major landing sections
- no `mandatory` snap
- if a section grows beyond viewport comfort, that section should opt out of snap behavior

Mobile:

- no hard or proximity snap required
- normal scrolling
- smaller and shorter transitions

## Content Priorities

The landing page should answer these questions in order:

1. What is this product?
2. Who is it for?
3. Why is it better than self-directed random study?
4. What features actually help me learn?
5. What should I do next?

## SEO and Metadata

This landing page is a public entry point and should include:

- page title focused on AI learning and guided skill development
- meta description in Vietnamese
- Open Graph title and description
- placeholder `og:image` plan if no asset is ready in this phase

This phase does not include full structured-data or sitemap redesign.

## Language Decision

This landing page is Vietnamese-first in this phase.

- all primary copy is in Vietnamese
- no multi-language support will be added in this PR

## Analytics Decision

Analytics integration is not introduced in this phase unless there is already a lightweight existing mechanism.

What we will still do:

- keep CTA structure explicit so event hooks can be added later
- name CTA components clearly for future tracking

## Asset Strategy

This phase should prefer code-native visuals:

- CSS gradients
- layout panels
- inline UI mockup blocks
- simple iconography already used in the codebase

This phase should not depend on:

- external illustration pipelines
- Lottie
- heavy video assets

## Accessibility Baseline

The landing page must support:

- keyboard navigation
- visible focus states
- color contrast at AA level for text and controls
- semantic heading order
- reduced-motion support

## Build Scope

### Phase 1: Landing page only

- replace root unauth homepage content
- add `PublicTopNav`
- add landing sections and CTA structure
- add team/contact footer
- add landing-specific styling support

### Phase 2: Public UI alignment follow-up

- review `/courses/...` public surfaces
- align public course overview styling with landing language

Phase 2 is explicitly out of scope for the first landing-page build.

## Out of Scope

The following are not part of this landing-page implementation:

- moving catalog to `/courses`
- redesigning authenticated app navigation
- redesigning `/courses/[courseSlug]`
- i18n or language switching
- new analytics platform integration
- new authentication flow changes

## Expected File Direction

Likely implementation areas for Phase 1:

- `frontend/app/page.tsx`
- a new public nav component under `frontend/components/layout/`
- new landing-specific components under `frontend/components/landing/`
- possible updates to `frontend/app/globals.css`

## Risks

- over-designing the landing page and weakening readability
- public nav accidentally behaving like app nav
- visual style drifting without enough token discipline
- scope creep into course pages
- snap behavior becoming awkward if sections become too tall

## Acceptance Criteria

These criteria must be verifiable.

- unauthenticated users can access `/` without redirect
- authenticated users can access `/` without redirect
- root landing page does not require authenticated API calls to render core content
- page clearly states support for AI/ML/CV/NLP skill development
- page clearly addresses all 3 audience groups in the copy structure
- personalized roadmap support has its own dedicated section
- AI chatbot learning support has its own dedicated section
- `Đăng ký ngay` links to `/register`
- `Đăng nhập` links to `/login`
- footer contains team and contact information
- desktop layout uses poster-style sections without hard mandatory snap
- mobile layout scrolls naturally
- reduced-motion users do not get parallax-style motion
- landing page metadata is present for title and description

## Test Plan

### Manual UAT

1. Visit `/` while logged out and confirm landing content appears.
2. Visit `/` while logged in and confirm landing content still appears.
3. Click `Đăng ký ngay` and confirm navigation to `/register`.
4. Click `Đăng nhập` and confirm navigation to `/login`.
5. Use public nav anchors and confirm scroll-to-section works.
6. Test mobile layout and confirm scrolling is natural and content is readable.
7. Test reduced motion preference and confirm major effects are suppressed.

### Automated checks

- route-level render test for the landing page
- public nav CTA link test
- auth redirect regression test for `/login`, `/register`, and `/forgot-password`

## Immediate Next Implementation Plan

1. Build `PublicTopNav` with anchor navigation and auth CTAs
2. Replace root homepage structure with landing-page sections
3. Build hero, roadmap, tutor, CTA, and footer sections
4. Add landing-specific layout and motion styles
5. Verify auth CTA and redirect behavior
6. Verify responsive layout and reduced-motion behavior
