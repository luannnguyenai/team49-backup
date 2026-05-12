"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { X } from "lucide-react";
import BottomSheet from "@/components/ui/BottomSheet";
import { learningUnitApi } from "@/lib/api";
import type { LearningUnitContentById } from "@/types";
import { formatDurationFromHours } from "../lib/duration";
import { getStatusLabel } from "../lib/status";
import { pathToFlow, sortByOrder } from "../presenters";
import { useLearningPathStore } from "../store";

function summarizeMarkdown(markdown: string | null | undefined): string | null {
  if (!markdown) return null;
  return markdown
    .replace(/^#+\s+/gm, "")
    .replace(/[`*_>#-]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 420);
}

function learningPlayerHref(item: { learn_href?: string | null; learning_unit_id: string }): string {
  return item.learn_href || `/learn/${item.learning_unit_id}`;
}

export default function LearningUnitDrawer() {
  const items = useLearningPathStore((s) => s.items);
  const selectedItemId = useLearningPathStore((s) => s.selectedItemId);
  const selectedSectionKey = useLearningPathStore((s) => s.selectedSectionKey);
  const closeDrawer = useLearningPathStore((s) => s.closeDrawer);
  const selectItem = useLearningPathStore((s) => s.selectItem);

  const [content, setContent] = useState<LearningUnitContentById | null>(null);
  const [contentError, setContentError] = useState<string | null>(null);
  const [isMobile, setIsMobile] = useState(false);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const lastActiveRef = useRef<Element | null>(null);

  const selectedItem = items.find((item) => item.id === selectedItemId) ?? null;
  const sections = useMemo(() => pathToFlow(items).sectionSummaries, [items]);
  const selectedSection = sections.find((section) => section.key === selectedSectionKey) ?? null;
  const ordered = useMemo(() => sortByOrder(items), [items]);
  const selectedIndex = selectedItem ? ordered.findIndex((item) => item.id === selectedItem.id) : -1;
  const previous = selectedIndex > 0 ? ordered[selectedIndex - 1] : null;
  const next = selectedIndex >= 0 && selectedIndex < ordered.length - 1 ? ordered[selectedIndex + 1] : null;
  const isOpen = Boolean(selectedItem || selectedSection);
  const title = selectedSection?.title ?? selectedItem?.learning_unit_title ?? "Lesson details";

  useEffect(() => {
    if (typeof window === "undefined") return;

    const mediaQuery = window.matchMedia("(max-width: 767px)");
    const updateIsMobile = () => setIsMobile(mediaQuery.matches);

    updateIsMobile();
    mediaQuery.addEventListener("change", updateIsMobile);

    return () => {
      mediaQuery.removeEventListener("change", updateIsMobile);
    };
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    lastActiveRef.current = document.activeElement;
    if (!isMobile) {
      closeButtonRef.current?.focus();
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeDrawer();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      if (lastActiveRef.current instanceof HTMLElement) lastActiveRef.current.focus();
    };
  }, [closeDrawer, isMobile, isOpen]);

  useEffect(() => {
    if (!selectedItem) {
      setContent(null);
      setContentError(null);
      return;
    }
    let active = true;
    setContentError(null);
    learningUnitApi
      .contentById(selectedItem.learning_unit_id)
      .then((data) => {
        if (active) setContent(data);
      })
      .catch(() => {
        if (active) setContentError("Unable to load the detailed description. You can still update the status or start learning.");
      });
    return () => {
      active = false;
    };
  }, [selectedItem]);

  if (!isOpen) return null;

  const drawerContent = selectedSection ? (
    <div className="space-y-3">
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        {selectedSection.items.length} lessons in this group.
      </p>
      {selectedSection.items.map((item) => (
        <button key={item.id} type="button" onClick={() => selectItem(item.id)} className="w-full rounded-xl border p-3 text-left hover:bg-slate-50 dark:hover:bg-slate-900" style={{ borderColor: "var(--border)" }}>
          <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{item.learning_unit_title}</p>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>{getStatusLabel(item.status)}</p>
        </button>
      ))}
    </div>
  ) : selectedItem ? (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-xl border p-3" style={{ borderColor: "var(--border)" }}>
          <p style={{ color: "var(--text-muted)" }}>Group</p>
          <p className="font-medium" style={{ color: "var(--text-primary)" }}>{selectedItem.section_title ?? "Other"}</p>
        </div>
        <div className="rounded-xl border p-3" style={{ borderColor: "var(--border)" }}>
          <p style={{ color: "var(--text-muted)" }}>Week / duration</p>
          <p className="font-medium" style={{ color: "var(--text-primary)" }}>
            Week {selectedItem.week_number ?? 1} · {formatDurationFromHours(selectedItem.estimated_hours) ?? "0 min"}
          </p>
        </div>
      </div>

      <div>
        <p className="mb-2 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Status</p>
        <span
          className="inline-flex items-center rounded-full border px-3 py-1.5 text-sm font-medium"
          style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
        >
          {getStatusLabel(selectedItem.status)}
        </span>
      </div>

      <div className="min-h-[7rem]">
        <p className="mb-2 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Description</p>
        {contentError ? (
          <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-200">{contentError}</p>
        ) : content ? (
          <p className="text-sm leading-6" style={{ color: "var(--text-secondary)" }}>
            {summarizeMarkdown(content.content_markdown) ?? "No detailed description is available yet."}
          </p>
        ) : (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>Loading description...</p>
        )}
      </div>

      <div className="flex items-center justify-between gap-2">
        {previous ? (
          <button
            type="button"
            className="rounded-lg border px-3 py-2 text-sm"
            style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
            onClick={() => selectItem(previous.id)}
          >
            Previous lesson
          </button>
        ) : (
          <span aria-hidden="true" />
        )}
        {next ? (
          <button
            type="button"
            className="rounded-lg border px-3 py-2 text-sm"
            style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
            onClick={() => selectItem(next.id)}
          >
            Next lesson
          </button>
        ) : (
          <span aria-hidden="true" />
        )}
      </div>

      <Link
        href={learningPlayerHref(selectedItem)}
        className="flex w-full items-center justify-center rounded-xl bg-primary-600 px-4 py-3 text-sm font-semibold text-white hover:opacity-90"
      >
        Start learning
      </Link>
    </div>
  ) : null;

  if (isMobile) {
    return (
      <BottomSheet open={isOpen} onOpenChange={(open) => { if (!open) closeDrawer(); }} title={title}>
        {drawerContent}
      </BottomSheet>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button className="absolute inset-0 bg-slate-950/30" aria-label="Close details panel" onClick={closeDrawer} />
      <aside className="relative h-full w-full max-w-xl overflow-y-auto border-l p-6 shadow-2xl" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
              {selectedSection ? "Lesson group" : "Lesson"}
            </p>
            <h2 className="mt-1 text-xl font-bold" style={{ color: "var(--text-primary)" }}>
              {title}
            </h2>
          </div>
          <button ref={closeButtonRef} type="button" onClick={closeDrawer} className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>
        {drawerContent}
      </aside>
    </div>
  );
}
