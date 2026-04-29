import { beforeEach, describe, expect, it, vi } from "vitest";

const courseApiMock = vi.hoisted(() => ({
  catalog: vi.fn(),
}));

const bootstrapDataApiMock = vi.hoisted(() => ({
  courses: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    courseApi: {
      ...actual.courseApi,
      catalog: courseApiMock.catalog,
    },
    bootstrapDataApi: {
      ...actual.bootstrapDataApi,
      courses: bootstrapDataApiMock.courses,
    },
  };
});

describe("course catalog cache", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    bootstrapDataApiMock.courses.mockResolvedValue([
      {
        id: "course_cs231n",
        slug: "cs231n",
        title: "CS231n: Deep Learning for Computer Vision",
        short_description: "Deep learning foundations for computer vision.",
        status: "ready",
        visibility: "public",
        cover_image_url: "/courses/cs231n/cover.jpg",
        hero_badge: "Available now",
        primary_subject: "computer_vision",
        sort_order: 2,
      },
    ]);
  });

  it("reuses the same in-flight request for repeated includeUnavailable=true calls", async () => {
    const response = { items: [] };
    courseApiMock.catalog.mockResolvedValue(response);

    const { getCachedAllCourseCatalog, resetCachedAllCourseCatalog } = await import(
      "@/lib/course-catalog-cache"
    );
    resetCachedAllCourseCatalog();

    const first = getCachedAllCourseCatalog(true);
    const second = getCachedAllCourseCatalog(true);

    const [firstResult, secondResult] = await Promise.all([first, second]);

    expect(firstResult).toBe(response);
    expect(secondResult).toBe(response);
    expect(courseApiMock.catalog).toHaveBeenCalledTimes(1);
    expect(courseApiMock.catalog).toHaveBeenCalledWith({
      view: "all",
      includeUnavailable: true,
    });
  });

  it("keeps separate cache entries for different includeUnavailable values", async () => {
    courseApiMock.catalog
      .mockResolvedValueOnce({ items: [{ id: "a" }] })
      .mockResolvedValueOnce({ items: [{ id: "b" }] });

    const { getCachedAllCourseCatalog, resetCachedAllCourseCatalog } = await import(
      "@/lib/course-catalog-cache"
    );
    resetCachedAllCourseCatalog();

    await getCachedAllCourseCatalog(true);
    await getCachedAllCourseCatalog(false);

    expect(courseApiMock.catalog).toHaveBeenCalledTimes(2);
    expect(courseApiMock.catalog).toHaveBeenNthCalledWith(1, {
      view: "all",
      includeUnavailable: true,
    });
    expect(courseApiMock.catalog).toHaveBeenNthCalledWith(2, {
      view: "all",
      includeUnavailable: false,
    });
  });

  it("restarts a stale in-flight request instead of waiting forever", async () => {
    vi.useFakeTimers();
    const stalePromise = new Promise<never>(() => {});
    const freshResponse = { items: [{ id: "fresh-course" }] };
    courseApiMock.catalog
      .mockReturnValueOnce(stalePromise)
      .mockResolvedValueOnce(freshResponse);

    const { getCachedAllCourseCatalog, resetCachedAllCourseCatalog } = await import(
      "@/lib/course-catalog-cache"
    );
    resetCachedAllCourseCatalog();

    void getCachedAllCourseCatalog(true);
    vi.advanceTimersByTime(10_001);
    const result = await getCachedAllCourseCatalog(true);

    expect(result).toBe(freshResponse);
    expect(courseApiMock.catalog).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });

  it("falls back to bootstrap catalog when the API request rejects", async () => {
    courseApiMock.catalog.mockRejectedValue(new Error("network down"));

    const { getCachedAllCourseCatalog, resetCachedAllCourseCatalog } = await import(
      "@/lib/course-catalog-cache"
    );
    resetCachedAllCourseCatalog();

    const result = await getCachedAllCourseCatalog(true);

    expect(result.items[0]?.slug).toBe("cs231n");
    expect(bootstrapDataApiMock.courses).toHaveBeenCalledTimes(1);
  });
});
