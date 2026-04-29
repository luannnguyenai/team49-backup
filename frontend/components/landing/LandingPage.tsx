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
} from "lucide-react";

import PublicTopNav from "@/components/layout/PublicTopNav";
import ScrollReveal from "@/components/landing/ScrollReveal";
import { MOCK_COURSES } from "@/lib/mock-course-catalog";

const audienceCards = [
  {
    title: "Người mới bắt đầu",
    description: "Đi từ nền tảng cơ bản đến AI/ML theo một hướng học bớt mù mờ hơn.",
    icon: Compass,
  },
  {
    title: "Sinh viên và self-learner",
    description: "Ghép kiến thức rời rạc thành một lộ trình học có mục tiêu rõ ràng.",
    icon: GraduationCap,
  },
  {
    title: "Người đi làm kỹ thuật",
    description: "Nâng cấp năng lực AI/ML/CV/NLP theo hướng thực dụng và có định hướng.",
    icon: BrainCircuit,
  },
] as const;

const roadmapPoints = [
  "Chọn mục tiêu học phù hợp với AI/ML/CV/NLP",
  "Xác định mức nền tảng hiện tại để tránh học lại lan man",
  "Đi theo roadmap rõ ràng thay vì nhảy giữa các course rời rạc",
] as const;

const tutorPoints = [
  "Hỏi ngay khi vướng khái niệm, công thức hoặc ý tưởng kỹ thuật",
  "Giữ nhịp học liên tục thay vì thoát ra ngoài để tự tìm manh mối",
  "Nhận hỗ trợ sát với nội dung đang học thay vì chat chung chung",
] as const;

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="inline-flex items-center gap-2 rounded-full border border-cyan-200/80 bg-white/70 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-cyan-700 dark:border-cyan-400/30 dark:bg-slate-900/70 dark:text-cyan-200">
      <Sparkles className="h-3.5 w-3.5" />
      {children}
    </p>
  );
}

function BulletList({ items }: { items: readonly string[] }) {
  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-3 text-sm leading-6 text-slate-600 dark:text-slate-200">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-cyan-500" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function LandingPage() {
  return (
    <div className="bg-surface-page text-text-strong dark:bg-slate-950 dark:text-white">
      <PublicTopNav />

      <main className="landing-scroll-shell md:snap-y md:snap-proximity">
        <section
          id="product"
          className="landing-panel relative overflow-hidden border-b border-border-subtle dark:border-slate-800 md:snap-start"
        >
          <div className="landing-panel-glow absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(99,102,241,0.18),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(34,211,238,0.18),_transparent_30%),linear-gradient(180deg,#f8fafc_0%,#ffffff_45%,#ecfeff_100%)] dark:bg-[radial-gradient(circle_at_top_left,_rgba(99,102,241,0.24),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(34,211,238,0.2),_transparent_30%),linear-gradient(180deg,#020617_0%,#0f172a_48%,#082f49_100%)]" />
          <div className="relative mx-auto grid min-h-[calc(100vh-73px)] max-w-7xl gap-14 px-4 py-16 md:px-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)] lg:items-center lg:py-20">
            <ScrollReveal className="space-y-8">
              <SectionLabel>Sản phẩm học AI có định hướng</SectionLabel>

              <div className="space-y-5">
                <h1 className="max-w-4xl text-4xl font-semibold leading-tight text-slate-950 dark:text-white md:text-5xl lg:text-6xl">
                  Học AI, ML, CV và NLP theo một lộ trình rõ ràng hơn
                </h1>
                <p className="max-w-2xl text-base leading-8 text-slate-600 dark:text-slate-200 md:text-lg">
                  Một nền tảng học tập giúp bạn định hướng, học có hệ thống và tiếp tục tiến lên
                  khi gặp phần khó.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <Link
                  href="/register"
                  className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
                >
                  Đăng ký ngay
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex items-center rounded-full border border-slate-200 bg-white/80 px-6 py-3 text-sm font-semibold text-slate-700 transition-colors hover:border-slate-300 hover:bg-white dark:border-slate-700 dark:bg-slate-900/80 dark:text-white dark:hover:border-slate-600 dark:hover:bg-slate-900"
                >
                  Đăng nhập
                </Link>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                {audienceCards.map(({ title, description, icon: Icon }) => (
                  <ScrollReveal
                    as="article"
                    key={title}
                    delayMs={80}
                    className="rounded-3xl border border-white/70 bg-white/70 p-5 shadow-[0_20px_60px_-35px_rgba(15,23,42,0.35)] backdrop-blur dark:border-slate-800 dark:bg-slate-900/75"
                  >
                    <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-600 via-cyan-500 to-teal-400 text-white">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h2 className="text-base font-semibold text-slate-950 dark:text-white">{title}</h2>
                    <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-200">{description}</p>
                  </ScrollReveal>
                ))}
              </div>
            </ScrollReveal>

            <ScrollReveal className="relative" delayMs={120}>
              <div className="absolute inset-x-6 top-10 h-32 rounded-full bg-cyan-400/25 blur-3xl" />
              <div className="relative overflow-hidden rounded-[32px] border border-slate-200/80 bg-slate-950 p-6 text-white shadow-[0_30px_80px_-40px_rgba(8,145,178,0.65)]">
                <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-cyan-200">AI Learning Hub</p>
                    <p className="mt-1 text-sm text-slate-200">Guided skill roadmap</p>
                  </div>
                  <div className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs font-semibold text-cyan-200">
                    Ready to start
                  </div>
                </div>

                <div className="mt-6 space-y-4">
                  <div className="rounded-3xl bg-gradient-to-br from-indigo-600 via-cyan-500 to-teal-400 p-[1px]">
                    <div className="rounded-[calc(1.5rem-1px)] bg-slate-950/90 p-5">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-semibold">Roadmap đang đề xuất</p>
                          <p className="mt-1 text-xs text-slate-300">
                            AI Foundations → Machine Learning → Computer Vision
                          </p>
                        </div>
                        <Network className="h-5 w-5 text-cyan-200" />
                      </div>
                      <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
                        <div className="h-full w-2/3 rounded-full bg-gradient-to-r from-cyan-300 via-cyan-400 to-teal-300" />
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
                      <p className="text-xs uppercase tracking-[0.22em] text-cyan-200">Roadmap</p>
                      <p className="mt-3 text-lg font-semibold">Cá nhân hóa theo mục tiêu</p>
                      <p className="mt-2 text-sm leading-6 text-slate-300">
                        Gợi ý lộ trình từ nền tảng hiện có thay vì học ngẫu nhiên.
                      </p>
                    </div>
                    <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
                      <p className="text-xs uppercase tracking-[0.22em] text-cyan-200">AI Tutor</p>
                      <p className="mt-3 text-lg font-semibold">Hỗ trợ khi đang học</p>
                      <p className="mt-2 text-sm leading-6 text-slate-300">
                        Hỏi ngay trong lúc học để không đứt nhịp suy nghĩ.
                      </p>
                    </div>
                  </div>

                  <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
                    <p className="text-sm font-semibold">Tập trung vào năng lực thực học</p>
                    <p className="mt-2 text-sm leading-6 text-slate-300">
                      Không chỉ hiển thị course. Landing page này dẫn người học tới một cách học
                      có định hướng, có hỗ trợ, và gắn chặt với AI/ML/CV/NLP.
                    </p>
                  </div>
                </div>
              </div>
            </ScrollReveal>
          </div>
        </section>

        <section
          id="roadmap"
          className="landing-panel relative border-b border-border-subtle bg-surface-card dark:border-slate-800 dark:bg-slate-950 md:snap-start"
        >
          <div className="mx-auto grid max-w-7xl gap-10 px-4 py-20 md:px-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:items-center">
            <ScrollReveal className="space-y-6">
              <SectionLabel>Cá nhân hóa lộ trình học</SectionLabel>
              <div className="space-y-4">
                <h2 className="text-3xl font-semibold leading-tight text-slate-950 dark:text-white md:text-4xl">
                  Cá nhân hóa lộ trình học
                </h2>
                <p className="max-w-xl text-base leading-8 text-slate-600 dark:text-slate-200">
                  Nền tảng giúp bạn biến mục tiêu học AI thành một hành trình cụ thể hơn, thay vì
                  tự ghép khóa học và tự đoán bước tiếp theo.
                </p>
              </div>
              <BulletList items={roadmapPoints} />
            </ScrollReveal>

            <div className="grid gap-4 md:grid-cols-3">
              <ScrollReveal
                as="article"
                className="rounded-[28px] border border-border-subtle bg-surface-card p-5 shadow-card dark:border-slate-800 dark:bg-slate-900"
              >
                <p className="text-xs uppercase tracking-[0.2em] text-cyan-700">01</p>
                <h3 className="mt-3 text-lg font-semibold text-slate-950 dark:text-white">Mục tiêu</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-200">
                  Chọn hướng học AI/ML/CV/NLP phù hợp với nhu cầu hiện tại.
                </p>
              </ScrollReveal>
              <ScrollReveal
                as="article"
                delayMs={80}
                className="rounded-[28px] border border-cyan-200 bg-cyan-50 p-5 shadow-sm dark:border-cyan-500/30 dark:bg-cyan-950/20"
              >
                <p className="text-xs uppercase tracking-[0.2em] text-cyan-700">02</p>
                <h3 className="mt-3 text-lg font-semibold text-slate-950 dark:text-white">Đánh giá nền tảng</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-200">
                  Xác định điểm bắt đầu hợp lý để học nhanh hơn và ít vòng vo hơn.
                </p>
              </ScrollReveal>
              <ScrollReveal
                as="article"
                delayMs={160}
                className="rounded-[28px] border border-border-subtle bg-surface-card p-5 shadow-card dark:border-slate-800 dark:bg-slate-900"
              >
                <p className="text-xs uppercase tracking-[0.2em] text-cyan-700">03</p>
                <h3 className="mt-3 text-lg font-semibold text-slate-950 dark:text-white">Tiến trình rõ ràng</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-200">
                  Học theo roadmap có thứ tự thay vì nhảy giữa các chủ đề rời rạc.
                </p>
              </ScrollReveal>
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
              <SectionLabel>AI Tutor đồng hành khi học</SectionLabel>
              <div className="space-y-4">
                <h2 className="text-3xl font-semibold leading-tight text-white md:text-4xl">
                  AI chatbot hỗ trợ ngay trong lúc học
                </h2>
                <p className="max-w-xl text-base leading-8 text-slate-300">
                  Khi bạn mắc ở một ý tưởng, công thức hay khái niệm, chatbot giúp kéo bạn trở lại
                  nhịp học thay vì để quá trình tự học bị đứt đoạn.
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
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-600 via-cyan-500 to-teal-400">
                      <Bot className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold">AI Tutor</p>
                      <p className="text-xs text-slate-400">Context-aware support</p>
                    </div>
                  </div>
                  <div className="mt-5 space-y-3 text-sm leading-6 text-slate-300">
                    <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                      Embedding và attention khác nhau ở đâu?
                    </div>
                    <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-cyan-100">
                      Attention giúp mô hình tập trung vào phần thông tin liên quan trong ngữ cảnh
                      hiện tại, còn embedding là cách biểu diễn token thành vector đầu vào.
                    </div>
                  </div>
                </div>

                <div className="rounded-[28px] border border-white/10 bg-white/5 p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-[0.22em] text-cyan-200">Study flow</p>
                      <p className="mt-2 text-lg font-semibold">Học, hỏi, rồi tiếp tục</p>
                    </div>
                    <MessagesSquare className="h-5 w-5 text-cyan-200" />
                  </div>
                  <div className="mt-5 space-y-3">
                    <div className="rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3">
                      <p className="text-sm font-medium">Lecture context</p>
                      <p className="mt-1 text-sm text-slate-300">
                        Tập trung vào đúng phần bài học bạn đang xem.
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3">
                      <p className="text-sm font-medium">Clarify fast</p>
                      <p className="mt-1 text-sm text-slate-300">
                        Giải thích nhanh để không bị mất đà tự học.
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3">
                      <p className="text-sm font-medium">Keep moving</p>
                      <p className="mt-1 text-sm text-slate-300">
                        Trở lại tiến độ học ngay thay vì phải đi tìm tài liệu ngoài luồng.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </ScrollReveal>
          </div>
        </section>

        <section className="landing-panel border-b border-border-subtle bg-surface-card dark:border-slate-800 dark:bg-slate-950 md:snap-start">
          <div className="mx-auto max-w-7xl px-4 py-20 md:px-6">
            <ScrollReveal className="space-y-6">
              <div className="space-y-4 text-center">
                <SectionLabel>Danh mục đang mở rộng</SectionLabel>
                <h2 className="text-3xl font-semibold leading-tight text-slate-950 dark:text-white md:text-4xl">
                  Nhiều khóa học hơn đang được chuẩn bị
                </h2>
                <p className="mx-auto max-w-3xl text-base leading-8 text-slate-600 dark:text-slate-200">
                  Đây là các hướng học sắp được mở thêm trong catalog. Chúng đã hiển thị với trạng
                  thái coming soon để người học nhìn thấy lộ trình mở rộng của nền tảng.
                </p>
              </div>

              <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                {MOCK_COURSES.map((course, index) => (
                  <ScrollReveal
                    as="article"
                    key={course.slug}
                    delayMs={index * 50}
                    className="rounded-[28px] border border-border-subtle bg-surface-card p-6 shadow-card dark:border-slate-800 dark:bg-slate-900"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-700 dark:text-cyan-200">
                          {course.hero_kicker}
                        </p>
                        <h3 className="mt-3 text-xl font-semibold text-slate-950 dark:text-white">
                          {course.title}
                        </h3>
                      </div>
                      <span className="rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-700 dark:border-cyan-500/30 dark:bg-cyan-950/30 dark:text-cyan-200">
                        {course.hero_badge}
                      </span>
                    </div>

                    <p className="mt-4 text-sm leading-7 text-slate-600 dark:text-slate-200">
                      {course.short_description}
                    </p>
                  </ScrollReveal>
                ))}
              </div>
            </ScrollReveal>
          </div>
        </section>

        <section className="landing-panel border-b border-border-subtle bg-surface-card dark:border-slate-800 dark:bg-slate-950 md:snap-start">
          <ScrollReveal className="mx-auto max-w-5xl px-4 py-20 text-center md:px-6">
            <SectionLabel>Bắt đầu học có định hướng</SectionLabel>
            <h2 className="mt-6 text-3xl font-semibold leading-tight text-slate-950 dark:text-white md:text-4xl">
              Nếu bạn muốn học AI bài bản hơn, bắt đầu từ đây
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-base leading-8 text-slate-600 dark:text-slate-200">
              Dành cho người mới, người tự học, và người đi làm kỹ thuật muốn xây dựng năng lực
              AI/ML/CV/NLP theo cách có cấu trúc hơn.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Link
                href="/register"
                className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
              >
                Đăng ký ngay
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/login"
                className="inline-flex items-center rounded-full border border-slate-200 px-6 py-3 text-sm font-semibold text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:text-white dark:hover:border-slate-600 dark:hover:bg-slate-900"
              >
                Đăng nhập
              </Link>
            </div>
          </ScrollReveal>
        </section>
      </main>

      <footer id="contact" className="bg-slate-950 text-white">
        <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 md:grid-cols-[minmax(0,1fr)_minmax(280px,0.8fr)] md:px-6">
          <ScrollReveal className="space-y-4">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-200">
              Đội ngũ phát triển
            </p>
            <h2 className="text-2xl font-semibold">Xây dựng một trải nghiệm học AI có định hướng hơn</h2>
            <p className="max-w-2xl text-sm leading-7 text-slate-300">
              Landing page này đại diện cho định hướng sản phẩm: giúp người học tiếp cận AI/ML/CV/NLP
              theo cách có cấu trúc, có hỗ trợ, và bớt phụ thuộc vào việc tự nối các mảnh kiến thức rời rạc.
            </p>
          </ScrollReveal>

          <ScrollReveal
            delayMs={120}
            className="rounded-[28px] border border-white/10 bg-white/5 p-6"
          >
            <p className="text-sm font-semibold text-white">Liên hệ</p>
            <div className="mt-4 space-y-3 text-sm text-slate-300">
              <p>Kênh hỗ trợ: đội ngũ phát triển nội bộ của dự án AI Learning Hub</p>
              <p>Liên hệ kỹ thuật: qua repository dự án và kênh phối hợp nội bộ hiện tại</p>
              <p>Phạm vi sản phẩm: guided learning, roadmap support, AI tutor for AI/ML/CV/NLP</p>
            </div>
          </ScrollReveal>
        </div>
      </footer>
    </div>
  );
}
