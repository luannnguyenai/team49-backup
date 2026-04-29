import { courseApi } from "@/lib/api";
import type { CourseCatalogResponse } from "@/types";

type CacheKey = "all:true" | "all:false";

type CacheEntry = {
  data: CourseCatalogResponse | null;
  promise: Promise<CourseCatalogResponse> | null;
  startedAt: number | null;
};

const REQUEST_STALE_MS = 10_000;

const catalogCache = new Map<CacheKey, CacheEntry>();

function getCacheKey(includeUnavailable: boolean): CacheKey {
  return includeUnavailable ? "all:true" : "all:false";
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

export function getCachedAllCourseCatalog(includeUnavailable: boolean): Promise<CourseCatalogResponse> {
  const key = getCacheKey(includeUnavailable);
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

  const request = courseApi.catalog({ view: "all", includeUnavailable });
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
