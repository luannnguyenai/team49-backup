"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { X } from "lucide-react";
import { learningUnitApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { LearningUnitContentById, PathStatus } from "@/types";
import { getStatusLabel } from "../lib/status";
import { pathToFlow, sortByOrder } from "../presenters";
import { useLearningPathStore } from "../store";

const STATUSES: PathStatus[] = ["pending", "in_progress", "completed", "skipped"];

function summarizeMarkdown(markdown: string | null | undefined): string | null {
  if (!markdown) return null;
  return markdown
    .replace(/^#+\s+/gm, "")
    .replace(/[`*_>#-]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 420);
}

export default function LearningUnitDrawer() {
  const items = useLearningPathStore((s) => s.items);
  const selectedItemId = useLearningPathStore((s) => s.selectedItemId);
  const selectedSectionKey = useLearningPathStore((s) => s.selectedSectionKey);
  const closeDrawer = useLearningPathStore((s) => s.closeDrawer);
  const selectItem = useLearningPathStore((s) => s.selectItem);
  const updateStatus = useLearningPathStore((s) => s.updateStatus);
  const updatingStatusById = useLearningPathStore((s) => s.updatingStatusById);

  const [content, setContent] = useState<LearningUnitContentById | null>(null);
  const [contentError, setContentError] = useState<string | null>(null);
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

  useEffect(() => {
    if (!isOpen) return;
    lastActiveRef.current = document.activeElement;
    closeButtonRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeDrawer();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      if (lastActiveRef.current instanceof HTMLElement) lastActiveRef.current.focus();
    };
  }, [closeDrawer, isOpen]);

  useEffect(() => {
    if (!selectedItem) {
      setContent(null);
      setContentError(null);
      return;
    }
    let active = true;
    setContent(null);
    setContentError(null);
    learningUnitApi
      .contentById(selectedItem.learning_unit_id)
      .then((data) => {
        if (active) setContent(data);
      })
      .catch(() => {
        if (active) setContentError("Không tải được mô tả chi tiết. Bạn vẫn có thể cập nhật trạng thái hoặc bắt đầu học.");
      });
    return () => {
      active = false;
    };
  }, [selectedItem]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button className="absolute inset-0 bg-slate-950/30" aria-label="Đóng bảng chi tiết" onClick={closeDrawer} />
      <aside className="relative h-full w-full max-w-xl overflow-y-auto border-l p-6 shadow-2xl" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
              {selectedSection ? "Nhóm bài học" : "Bài học"}
            </p>
            <h2 className="mt-1 text-xl font-bold" style={{ color: "var(--text-primary)" }}>
              {selectedSection?.title ?? selectedItem?.learning_unit_title}
            </h2>
          </div>
          <button ref={closeButtonRef} type="button" onClick={closeDrawer} className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Đóng">
            <X className="h-5 w-5" />
          </button>
        </div>

        {selectedSection ? (
          <div className="space-y-3">
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              {selectedSection.items.length} bài học trong nhóm này.
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
                <p style={{ color: "var(--text-muted)" }}>Nhóm</p>
                <p className="font-medium" style={{ color: "var(--text-primary)" }}>{selectedItem.section_title ?? "Khác"}</p>
              </div>
              <div className="rounded-xl border p-3" style={{ borderColor: "var(--border)" }}>
                <p style={{ color: "var(--text-muted)" }}>Tuần / thời lượng</p>
                <p className="font-medium" style={{ color: "var(--text-primary)" }}>Tuần {selectedItem.week_number ?? 1} · {selectedItem.estimated_hours ?? 0}h</p>
              </div>
            </div>

            <div>
              <p className="mb-2 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Trạng thái</p>
              <div className="flex flex-wrap gap-2">
                {STATUSES.map((status) => (
                  <button
                    key={status}
                    type="button"
                    disabled={updatingStatusById[selectedItem.id]}
                    onClick={() => updateStatus(selectedItem.id, status)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-sm font-medium disabled:opacity-60",
                      selectedItem.status === status ? "border-primary-600 bg-primary-600 text-white" : "hover:bg-slate-50 dark:hover:bg-slate-900",
                    )}
                    style={selectedItem.status !== status ? { borderColor: "var(--border)", color: "var(--text-secondary)" } : undefined}
                  >
                    {getStatusLabel(status)}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <p className="mb-2 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Mô tả</p>
              {contentError ? (
                <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-200">{contentError}</p>
              ) : content ? (
                <p className="text-sm leading-6" style={{ color: "var(--text-secondary)" }}>
                  {summarizeMarkdown(content.content_markdown) ?? "Chưa có mô tả chi tiết."}
                </p>
              ) : (
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>Đang tải mô tả...</p>
              )}
            </div>

            <div className="flex gap-2">
              {previous && (
                <button
                  type="button"
                  className="rounded-lg border px-3 py-2 text-sm"
                  style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
                  onClick={() => selectItem(previous.id)}
                >
                  Bài trước
                </button>
              )}
              {next && (
                <button
                  type="button"
                  className="rounded-lg border px-3 py-2 text-sm"
                  style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
                  onClick={() => selectItem(next.id)}
                >
                  Bài tiếp
                </button>
              )}
            </div>

            <Link
              href={`/learn/${selectedItem.learning_unit_id}`}
              className="flex w-full items-center justify-center rounded-xl bg-primary-600 px-4 py-3 text-sm font-semibold text-white hover:opacity-90"
            >
              Bắt đầu học
            </Link>
          </div>
        ) : null}
      </aside>
    </div>
  );
}
