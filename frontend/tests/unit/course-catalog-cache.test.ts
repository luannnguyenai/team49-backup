import { beforeEach, describe, expect, it, vi } from "vitest";

const courseApiMock = vi.hoisted(() => ({
  catalog: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    courseApi: {
      ...actual.courseApi,
      catalog: courseApiMock.catalog,
    },
  };
});

describe("course catalog cache", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
});
