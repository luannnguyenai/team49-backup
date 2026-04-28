import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "@/app/page";
import CourseOverviewInteractive from "@/components/course/CourseOverviewInteractive";
import type { CourseOverviewResponse } from "@/types";

describe("landing page route", () => {
  it("renders a public landing page focused on guided AI learning", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", {
        name: "Học AI, ML, CV và NLP theo một lộ trình rõ ràng hơn",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Một nền tảng học tập giúp bạn định hướng, học có hệ thống và tiếp tục tiến lên khi gặp phần khó."),
    ).toBeInTheDocument();
    expect(
      screen
        .getAllByRole("link", { name: "Đăng ký ngay" })
        .every((link) => link.getAttribute("href") === "/register"),
    ).toBe(true);
    expect(
      screen
        .getAllByRole("link", { name: "Đăng nhập" })
        .every((link) => link.getAttribute("href") === "/login"),
    ).toBe(true);
    expect(screen.getByRole("link", { name: "Sản phẩm" })).toHaveAttribute("href", "#product");
    expect(screen.getByRole("link", { name: "Lộ trình học" })).toHaveAttribute("href", "#roadmap");
    expect(screen.getByRole("link", { name: "AI Tutor" })).toHaveAttribute("href", "#tutor");
    expect(screen.getByRole("link", { name: "Liên hệ" })).toHaveAttribute("href", "#contact");
    expect(
      screen.getByRole("heading", { name: "Cá nhân hóa lộ trình học" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "AI chatbot hỗ trợ ngay trong lúc học" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Đội ngũ phát triển")).toBeInTheDocument();
  });
});

describe("course overview routes", () => {
  it("shows a startable overview for CS231n", () => {
    const data: CourseOverviewResponse = {
      course: {
        id: "course_cs231n",
        slug: "cs231n",
        title: "CS231n: Deep Learning for Computer Vision",
        short_description: "Deep learning foundations for computer vision.",
        status: "ready",
        cover_image_url: "/courses/cs231n/cover.jpg",
        hero_badge: "Available now",
        is_recommended: false,
      },
      overview: {
        headline: "Build deep intuition for modern vision systems",
        subheadline: "Learn the path from linear classifiers to transformers.",
        summary_markdown: "Course summary...",
        learning_outcomes: ["Understand the core architecture families used in computer vision"],
        target_audience: "Learners with Python basics",
        prerequisites_summary: "Comfort with Python",
        estimated_duration_text: "18 lectures",
        structure_snapshot: { summary: "Lecture-first course" },
        cta_label: "Start learning",
      },
      entry: {
        decision: "redirect",
        target: "/courses/cs231n/start",
        reason: "learning_ready",
      },
    };

    render(
      <CourseOverviewInteractive courseSlug="cs231n" data={data} />,
    );

    expect(screen.getByText("Build deep intuition for modern vision systems")).toBeInTheDocument();
    expect(screen.getByText("Những gì bạn sẽ học")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start learning" })).toBeEnabled();
  });

  it("shows a startable overview for CS224n", () => {
    const data: CourseOverviewResponse = {
      course: {
        id: "course_cs224n",
        slug: "cs224n",
        title: "CS224n: Natural Language Processing with Deep Learning",
        short_description: "Modern NLP systems and language modeling.",
        status: "ready",
        cover_image_url: "/courses/cs224n/cover.jpg",
        hero_badge: "Available now",
        is_recommended: false,
      },
      overview: {
        headline: "Explore modern NLP and language modeling workflows",
        subheadline: "Learn the path from word vectors to transformers.",
        summary_markdown: "Course overview.",
        learning_outcomes: ["Build intuition for modern NLP systems"],
        target_audience: "Learners interested in NLP",
        prerequisites_summary: "Basic Python",
        estimated_duration_text: "Lecture-first course",
        structure_snapshot: { summary: "Lecture-first course with canonical sections" },
        cta_label: "Start learning",
      },
      entry: {
        decision: "redirect",
        target: "/courses/cs224n/start",
        reason: "learning_ready",
      },
    };

    render(
      <CourseOverviewInteractive courseSlug="cs224n" data={data} />,
    );

    expect(
      screen.getByText("Explore modern NLP and language modeling workflows"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start learning" })).toBeEnabled();
  });
});
