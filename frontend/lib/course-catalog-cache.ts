import { bootstrapDataApi, courseApi } from "@/lib/api";
import { mergeMockCourses } from "@/lib/mock-course-catalog";
import type { BootstrapCourse, CourseCatalogItem, CourseCatalogResponse } from "@/types";

type CacheKey = string;

type CacheEntry = {
  data: CourseCatalogResponse | null;
  promise: Promise<CourseCatalogResponse> | null;
  startedAt: number | null;
};

const REQUEST_STALE_MS = 10_000;
const API_TIMEOUT_MS = 3_000;

const catalogCache = new Map<CacheKey, CacheEntry>();

function getCacheKey(includeUnavailable: boolean, scope: string): CacheKey {
  return `all:${includeUnavailable ? "true" : "false"}:${scope}`;
}

function getOrCreateEntry(key: CacheKey): CacheEntry {
  const existing = catalogCache.get(key);
  if (existing) {
    return existing;
  }

  const created: CacheEntry = {
    data: null,
    promise: null,
    startedAt: null,
  };
  catalogCache.set(key, created);
  return created;
}

function toCatalogItem(course: BootstrapCourse): CourseCatalogItem {
  return {
    id: course.id,
    slug: course.slug,
    title: course.title,
    short_description: course.short_description,
    status: course.status === "ready" ? "ready" : "coming_soon",
    cover_image_url: course.cover_image_url,
    hero_badge: course.hero_badge,
    is_recommended: false,
    progress_percent: null,
  };
}

async function loadBootstrapCatalog(): Promise<CourseCatalogResponse> {
  const bootstrapCourses = await bootstrapDataApi.courses();
  return mergeMockCourses({
    items: bootstrapCourses.map(toCatalogItem),
  });
}

async function loadCatalogResponse(includeUnavailable: boolean): Promise<CourseCatalogResponse> {
  const timeoutPromise = new Promise<CourseCatalogResponse>((resolve) => {
    setTimeout(async () => {
      resolve(await loadBootstrapCatalog());
    }, API_TIMEOUT_MS);
  });

  try {
    return await Promise.race([
      courseApi.catalog({ view: "all", includeUnavailable }),
      timeoutPromise,
    ]);
  } catch {
    return loadBootstrapCatalog();
  }
}

export function getCachedAllCourseCatalog(
  includeUnavailable: boolean,
  scope = "public",
): Promise<CourseCatalogResponse> {
  const key = getCacheKey(includeUnavailable, scope);
  const entry = getOrCreateEntry(key);

  if (entry.data) {
    return Promise.resolve(entry.data);
  }

  const now = Date.now();
  const promiseIsFresh =
    entry.promise !== null &&
    entry.startedAt !== null &&
    now - entry.startedAt < REQUEST_STALE_MS;

  if (promiseIsFresh && entry.promise) {
    return entry.promise;
  }

  const request = loadCatalogResponse(includeUnavailable);
  entry.promise = request;
  entry.startedAt = now;

  request
    .then((response) => {
      if (entry.promise === request) {
        entry.data = response;
        entry.promise = null;
        entry.startedAt = null;
      }
    })
    .catch(() => {
      if (entry.promise === request) {
        entry.promise = null;
        entry.startedAt = null;
      }
    });

  return request;
}

export function resetCachedAllCourseCatalog(): void {
  catalogCache.clear();
}
