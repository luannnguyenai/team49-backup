 "use client";

import Link from "next/link";
import {
  ArrowRight,
  Bot,
  BrainCircuit,
  CheckCircle2,
  Compass,
  GraduationCap,
  MessagesSquare,
  Network,
  Sparkles,
  TrendingUp,
  Target,
  MapPin,
  Flag,
  Search,
} from "lucide-react";

import PublicTopNav from "@/components/layout/PublicTopNav";
import ScrollReveal from "@/components/landing/ScrollReveal";
import { MOCK_COURSES } from "@/lib/mock-course-catalog";

const audienceCards = [
  {
    title: "Beginners",
    description: "Start with a learning path that feels clearer, calmer, and easier to follow.",
    icon: Compass,
  },
  {
    title: "Self-paced learners",
    description: "Turn scattered studying into a more organized path with clear next steps.",
    icon: GraduationCap,
  },
  {
    title: "Learners rebuilding foundations",
    description: "Get back on track with a path that helps you study in the right order.",
    icon: BrainCircuit,
  },
] as const;

const roadmapPoints = [
  "Choose a learning direction without getting overwhelmed by too many starting points",
  "Assess your current foundation so you can start at the right level",
  "Follow a clear path instead of jumping between disconnected lessons and resources",
] as const;

const tutorPoints = [
  "Ask for help the moment something stops making sense",
  "Keep your momentum instead of leaving to search through scattered explanations",
  "Get support that stays connected to the lesson you are already studying",
] as const;

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="inline-flex items-center gap-2 rounded-full border border-cyan-200/80 bg-white/70 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-cyan-700">
      <Sparkles className="h-3.5 w-3.5" />
      {children}
    </p>
  );
}

function BulletList({ items }: { items: readonly string[] }) {
  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-3 text-sm leading-6 text-slate-600">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-cyan-500" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function LandingPage() {
  return (
    <div className="bg-surface-page text-text-strong">
      <PublicTopNav />

      <main className="landing-scroll-shell md:snap-y md:snap-proximity">
        <section
          id="product"
          className="landing-panel relative overflow-hidden border-b border-border-subtle md:snap-start"
        >
          <div className="landing-panel-glow absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(99,102,241,0.18),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(34,211,238,0.18),_transparent_30%),linear-gradient(180deg,#f8fafc_0%,#ffffff_45%,#ecfeff_100%)]" />
          <div className="relative mx-auto grid min-h-[calc(100vh-73px)] max-w-7xl gap-10 px-4 pb-12 pt-5 md:px-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)] lg:items-center lg:gap-14 lg:pb-20 lg:pt-10">
            <ScrollReveal className="space-y-8">
              <SectionLabel>Structured learning experience</SectionLabel>

              <div className="space-y-5">
                <h1 className="text-5xl font-extrabold leading-[1.1] tracking-tight text-slate-900 md:text-6xl lg:text-7xl">
                  Your Personal <br />
                  <span className="bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
                    Path to Mastery
                  </span>
                </h1>
                <p className="max-w-lg text-lg leading-relaxed text-slate-600 md:text-xl">
                  Adaptive, tailored learning modules created just for your goals.
                </p>
              </div>

              <div className="flex justify-center">
                <Link
                  href="/login?from=%2Fonboarding"
                  className="btn-primary group flex h-14 w-full items-center justify-center gap-3 rounded-full bg-blue-600 px-8 text-lg font-semibold text-white transition-all hover:bg-blue-700 hover:shadow-xl hover:shadow-blue-200 active:scale-[0.98] sm:w-auto min-w-[280px]"
                >
                  Get Your Own Learning Path
                  <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
                </Link>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                {audienceCards.map(({ title, description, icon: Icon }) => (
                  <ScrollReveal
                    as="article"
                    key={title}
                    delayMs={80}
                    className="rounded-3xl border border-white/70 bg-white/70 p-4 shadow-[0_20px_60px_-35px_rgba(15,23,42,0.35)] backdrop-blur sm:p-5"
                  >
                    <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl hero-gradient text-white">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h2 className="text-base font-semibold text-slate-950">{title}</h2>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
                  </ScrollReveal>
                ))}
              </div>
            </ScrollReveal>

            <ScrollReveal className="relative" delayMs={120}>
              <div className="relative aspect-square w-full max-w-[600px] flex items-center justify-center mx-auto lg:ml-auto">
                {/* Enhanced Background Glows for deeper colors */}
                <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_center,_rgba(34,211,238,0.4)_0%,_transparent_70%)] blur-3xl" />
                <div className="absolute -inset-4 -z-10 bg-[radial-gradient(circle_at_top_right,_rgba(99,102,241,0.3)_0%,_transparent_60%)] blur-2xl" />
                
                <div className="relative z-0 h-full w-full overflow-hidden rounded-[3rem] shadow-[0_32px_64px_-16px_rgba(8,145,178,0.3)] border border-white/20">
                  <img 
                    src="/images/landing-hero.png" 
                    alt="AI Learning Path Illustration" 
                    className="h-full w-full object-cover brightness-[1.02] contrast-[1.05] saturate-[1.1]"
                  />
                  <div className="absolute inset-0 bg-gradient-to-tr from-white/20 via-transparent to-transparent mix-blend-overlay" />
                  <div className="absolute inset-0 bg-cyan-900/5 mix-blend-multiply" />
                </div>
                
                {/* Floating Badges */}
                <div className="absolute top-[15%] left-[-5%] z-10 flex items-center gap-2 rounded-2xl border border-white bg-white/80 p-3 shadow-lg backdrop-blur-md">
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                    <TrendingUp className="h-4 w-4" />
                  </div>
                  <span className="pr-2 text-sm font-bold text-slate-700">Skill</span>
                </div>
                
                <div className="absolute bottom-[25%] left-[5%] z-10 flex items-center gap-2 rounded-2xl border border-white bg-white/80 p-3 shadow-lg backdrop-blur-md">
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <span className="pr-2 text-sm font-bold text-slate-700">Current Level</span>
                </div>
                
                <div className="absolute top-[30%] right-[-5%] z-10 flex items-center gap-2 rounded-2xl border border-orange-100 bg-orange-50 p-3 shadow-lg backdrop-blur-md">
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-orange-100 text-orange-600">
                    <Target className="h-4 w-4" />
                  </div>
                  <span className="pr-2 text-sm font-bold text-orange-700">Goal Achieved</span>
                </div>
              </div>
            </ScrollReveal>
          </div>
        </section>

        <section
          id="roadmap"
          className="landing-panel relative border-b border-border-subtle bg-surface-card md:snap-start"
        >
          <div className="mx-auto grid max-w-7xl gap-10 px-4 py-20 md:px-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:items-center">
            <ScrollReveal className="space-y-6">
              <SectionLabel>Personalized learning path</SectionLabel>
              <div className="space-y-4">
                <h2 className="text-3xl font-semibold leading-tight text-slate-950 md:text-4xl">
                  Personalized learning path
                </h2>
                <p className="max-w-xl text-base leading-8 text-slate-600">
                  Instead of piecing together lessons on your own, follow a path that gives you a
                  clearer starting point and a more natural next step.
                </p>
              </div>
              <BulletList items={roadmapPoints} />
            </ScrollReveal>

            <div className="relative">
              {/* Connecting Line (Horizontal on desktop) */}
              <div className="absolute left-0 top-12 hidden h-0.5 w-full bg-slate-100 lg:block" />
              
              <div className="relative grid gap-8 md:grid-cols-3 lg:gap-12">
                {/* Step 01 */}
                <ScrollReveal
                  as="article"
                  className="group relative flex flex-col items-center text-center"
                >
                  <div className="relative z-10 mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border-4 border-white bg-slate-50 text-slate-400 shadow-sm transition-all group-hover:scale-110 group-hover:border-cyan-100 group-hover:text-cyan-500">
                    <Compass className="h-7 w-7" />
                    <div className="absolute -right-1 -top-1 flex h-6 w-6 items-center justify-center rounded-full bg-slate-900 text-[10px] font-bold text-white">
                      01
                    </div>
                  </div>
                  <h3 className="text-xl font-bold text-slate-900">Direction</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-500">
                    Start with a learning direction that fits what you need right now.
                  </p>
                </ScrollReveal>

                {/* Step 02 - Highlighted */}
                <ScrollReveal
                  as="article"
                  delayMs={80}
                  className="group relative flex flex-col items-center text-center"
                >
                  {/* Connecting Line (Mobile/Tablet vertical) */}
                  <div className="absolute -top-8 left-1/2 h-8 w-0.5 -translate-x-1/2 bg-slate-100 md:hidden" />
                  
                  <div className="relative z-10 mb-6 flex h-20 w-20 items-center justify-center rounded-[2rem] border-4 border-cyan-50 bg-cyan-100 text-cyan-600 shadow-[0_0_30px_rgba(34,211,238,0.3)] transition-all scale-110 group-hover:scale-125">
                    <Search className="h-9 w-9" />
                    <div className="absolute -right-1 -top-1 flex h-7 w-7 items-center justify-center rounded-full bg-cyan-600 text-[11px] font-bold text-white shadow-lg">
                      02
                    </div>
                    {/* Pulsing Highlight */}
                    <div className="absolute inset-0 -z-10 animate-ping rounded-[2rem] bg-cyan-400 opacity-20" />
                  </div>
                  
                  <div className="rounded-3xl border border-cyan-100 bg-cyan-50/50 p-4 backdrop-blur-sm">
                    <h3 className="text-xl font-bold text-slate-900">Baseline assessment</h3>
                    <p className="mt-3 text-sm leading-6 text-slate-600 font-medium">
                      Find a starting point that matches your foundation so you can avoid unnecessary detours.
                    </p>
                  </div>
                </ScrollReveal>

                {/* Step 03 */}
                <ScrollReveal
                  as="article"
                  delayMs={160}
                  className="group relative flex flex-col items-center text-center"
                >
                  {/* Connecting Line (Mobile/Tablet vertical) */}
                  <div className="absolute -top-8 left-1/2 h-8 w-0.5 -translate-x-1/2 bg-slate-100 md:hidden" />

                  <div className="relative z-10 mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border-4 border-white bg-slate-50 text-slate-400 shadow-sm transition-all group-hover:scale-110 group-hover:border-cyan-100 group-hover:text-cyan-500">
                    <Flag className="h-7 w-7" />
                    <div className="absolute -right-1 -top-1 flex h-6 w-6 items-center justify-center rounded-full bg-slate-900 text-[10px] font-bold text-white">
                      03
                    </div>
                  </div>
                  <h3 className="text-xl font-bold text-slate-900">Clear progression</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-500">
                    Move through an ordered path instead of hopping between disconnected topics.
                  </p>
                </ScrollReveal>
              </div>
            </div>
          </div>
        </section>

        <section
          id="tutor"
          className="landing-panel relative overflow-hidden border-b border-slate-800 bg-slate-950 text-white md:snap-start"
        >
          <div className="landing-panel-glow absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(34,211,238,0.18),_transparent_30%),radial-gradient(circle_at_bottom_left,_rgba(99,102,241,0.18),_transparent_32%)]" />
          <div className="relative mx-auto grid max-w-7xl gap-10 px-4 py-20 md:px-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:items-center">
            <ScrollReveal className="space-y-6">
              <SectionLabel>Stay in your learning flow</SectionLabel>
              <div className="space-y-4">
                <h2 className="text-3xl font-semibold leading-tight text-white md:text-4xl">
                  Support that keeps you learning
                </h2>
                <p className="max-w-xl text-base leading-8 text-slate-300">
                  When you get stuck, the tutor helps you get unstuck without turning one confusing
                  moment into a lost study session.
                </p>
              </div>
              <BulletList items={tutorPoints} />
            </ScrollReveal>

            <ScrollReveal
              className="rounded-[32px] border border-white/10 bg-white/5 p-5 shadow-[0_30px_80px_-40px_rgba(34,211,238,0.5)] backdrop-blur"
              delayMs={120}
            >
              <div className="grid gap-4 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
                <div className="rounded-[28px] border border-white/10 bg-slate-900/80 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl hero-gradient">
                      <Bot className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold">AI Tutor</p>
                      <p className="text-xs text-slate-400">Context-aware support</p>
                    </div>
                  </div>
                  <div className="mt-5 space-y-3 text-sm leading-6 text-slate-300">
                    <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                      What is the difference between embeddings and attention?
                    </div>
                    <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-cyan-100">
                      Attention helps the model focus on the most relevant information in the
                      current context, while embeddings represent tokens as input vectors.
                    </div>
                  </div>
                </div>

                <div className="rounded-[28px] border border-white/10 bg-white/5 p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-[0.22em] text-cyan-200">Study flow</p>
                      <p className="mt-2 text-lg font-semibold">Study, ask, and keep going</p>
                    </div>
                    <MessagesSquare className="h-5 w-5 text-cyan-200" />
                  </div>
                  <div className="mt-5 space-y-3">
                    <div className="rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3">
                      <p className="text-sm font-medium">Lecture context</p>
                      <p className="mt-1 text-sm text-slate-300">
                        Stay focused on the exact part of the lesson you are viewing.
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3">
                      <p className="text-sm font-medium">Clarify fast</p>
                      <p className="mt-1 text-sm text-slate-300">
                        Get a quick explanation before confusion starts to slow you down.
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3">
                      <p className="text-sm font-medium">Keep moving</p>
                      <p className="mt-1 text-sm text-slate-300">
                        Return to your progress immediately instead of hunting for outside material.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </ScrollReveal>
          </div>
        </section>

        <section className="landing-panel border-b border-border-subtle bg-surface-card md:snap-start">
          <div className="mx-auto max-w-7xl px-4 py-20 md:px-6">
            <ScrollReveal className="space-y-6">
              <div className="space-y-4 text-center">
                <SectionLabel>Catalog in progress</SectionLabel>
                <h2 className="text-3xl font-semibold leading-tight text-slate-950 md:text-4xl">
                  More learning paths are on the way
                </h2>
                <p className="mx-auto max-w-3xl text-base leading-8 text-slate-600">
                  These upcoming additions show how the platform will keep expanding into new
                  learning directions while preserving the same guided experience.
                </p>
              </div>

              <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                {MOCK_COURSES.map((course, index) => (
                  <ScrollReveal
                    as="article"
                    key={course.slug}
                    delayMs={index * 50}
                    className="rounded-[28px] border border-border-subtle bg-surface-card p-6 shadow-card"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-700">
                          {course.hero_kicker}
                        </p>
                        <h3 className="mt-3 text-xl font-semibold text-slate-950">
                          {course.title}
                        </h3>
                      </div>
                      <span className="rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-700">
                        {course.hero_badge}
                      </span>
                    </div>

                    <p className="mt-4 text-sm leading-7 text-slate-600">
                      {course.short_description}
                    </p>
                  </ScrollReveal>
                ))}
              </div>
            </ScrollReveal>
          </div>
        </section>

        <section className="landing-panel border-b border-border-subtle bg-surface-card md:snap-start">
          <ScrollReveal className="mx-auto max-w-5xl px-4 py-20 text-center md:px-6">
            <SectionLabel>Start with direction</SectionLabel>
            <h2 className="mt-6 text-3xl font-semibold leading-tight text-slate-950 md:text-4xl">
              Start with a path that feels easier to follow
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-base leading-8 text-slate-600">
              Built for beginners and self-learners who want to study with more structure, less
              guesswork, and a clearer sense of what comes next.
            </p>
            <div className="mt-8 flex justify-center">
              <Link
                href="/login?from=%2Fonboarding"
                className="btn-primary group flex h-14 w-full items-center justify-center gap-3 rounded-full bg-blue-600 px-8 text-lg font-semibold text-white transition-all hover:bg-blue-700 hover:shadow-xl hover:shadow-blue-200 active:scale-[0.98] sm:w-auto min-w-[280px]"
              >
                Get Your Own Learning Path
                <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
              </Link>
            </div>
          </ScrollReveal>
        </section>
      </main>

      <footer id="contact" className="bg-slate-950 text-white">
        <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 md:grid-cols-[minmax(0,1fr)_minmax(280px,0.8fr)] md:px-6">
          <ScrollReveal className="space-y-4">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-200">
              AI in Action
            </p>
            <h2 className="text-2xl font-semibold">Dự án VinLearn</h2>
            <p className="max-w-2xl text-sm leading-7 text-slate-300">
              Dự án thuộc khuôn khổ chương trình AI IN ACTION thuộc VinUniversity,
              Tập Đoàn VinGroup.
            </p>
          </ScrollReveal>

          <ScrollReveal
            delayMs={120}
            className="rounded-[28px] border border-white/10 bg-white/5 p-6"
          >
            <p className="text-sm font-semibold text-white">Dev team liên hệ</p>
            <ul className="mt-4 space-y-3 text-sm text-slate-300">
              <li>Nguyễn Duy Minh Hoàng</li>
              <li>Nguyễn Đôn Đức</li>
              <li>Nguyễn Lê Minh Luân</li>
            </ul>
          </ScrollReveal>
        </div>
      </footer>
    </div>
  );
}
