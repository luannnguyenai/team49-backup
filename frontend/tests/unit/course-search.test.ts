import { describe, expect, it } from "vitest";

import {
  COMING_SOON_ITEM,
  CS224N_ITEM,
  CS231N_ITEM,
} from "@/tests/fixtures/coursePlatform";
import {
  filterCoursesByQuery,
  matchesCourseQuery,
  normalizeCourseSearchQuery,
} from "@/lib/course-search";

describe("course search utilities", () => {
  const COURSES = [
    CS231N_ITEM,
    CS224N_ITEM,
    {
      ...COMING_SOON_ITEM,
      title: "Nhập môn AI ứng dụng",
      short_description: "Lộ trình nhập môn dành cho người mới bắt đầu với AI thực chiến.",
      hero_kicker: "AI foundations",
    },
  ];

  it("normalizes vietnamese diacritics, casing, and whitespace", () => {
    expect(normalizeCourseSearchQuery("  NHẬP   MÔN  ")).toBe("nhap mon");
  });

  it("treats queries shorter than two characters as empty", () => {
    expect(filterCoursesByQuery(COURSES, "a")).toEqual(COURSES);
  });

  it("matches a course title accent-insensitively", () => {
    expect(matchesCourseQuery(COURSES[2], "nhap mon")).toBe(true);
  });

  it("matches by short description", () => {
    const filtered = filterCoursesByQuery(COURSES, "computer vision");

    expect(filtered).toEqual([CS231N_ITEM]);
  });

  it("matches by hero kicker when present", () => {
    const filtered = filterCoursesByQuery(COURSES, "ai foundations");

    expect(filtered).toEqual([COURSES[2]]);
  });

  it("returns an empty list when no course matches", () => {
    expect(filterCoursesByQuery(COURSES, "graph rag systems")).toEqual([]);
  });
});
