import { courseApi } from "@/lib/api";
import type { CourseCatalogResponse } from "@/types";

type CacheKey = "all:true" | "all:false";

const catalogPromiseCache = new Map<CacheKey, Promise<CourseCatalogResponse>>();

function getCacheKey(includeUnavailable: boolean): CacheKey {
  return includeUnavailable ? "all:true" : "all:false";
}

export function getCachedAllCourseCatalog(includeUnavailable: boolean): Promise<CourseCatalogResponse> {
  const key = getCacheKey(includeUnavailable);
  const existing = catalogPromiseCache.get(key);
  if (existing) {
    return existing;
  }

  const request = courseApi.catalog({ view: "all", includeUnavailable }).catch((error) => {
    catalogPromiseCache.delete(key);
    throw error;
  });

  catalogPromiseCache.set(key, request);
  return request;
}

export function resetCachedAllCourseCatalog(): void {
  catalogPromiseCache.clear();
}
