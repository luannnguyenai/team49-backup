"use client";

import { useEffect, useId, useRef } from "react";

import { cn } from "@/lib/utils";

type BottomSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  panelClassName?: string;
};

export default function BottomSheet({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  className,
  panelClassName,
}: BottomSheetProps) {
  const titleId = useId();
  const descriptionId = useId();
  const lastActiveElementRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (open) {
      lastActiveElementRef.current = document.activeElement as HTMLElement | null;
      return;
    }

    lastActiveElementRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onOpenChange(false);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onOpenChange, open]);

  if (!open) {
    return null;
  }

  return (
    <div className={cn("mobile-sheet-backdrop", className)}>
      <button
        type="button"
        data-testid="bottom-sheet-backdrop"
        aria-label="Close sheet"
        className="absolute inset-0 cursor-default"
        onClick={() => onOpenChange(false)}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        className={cn("mobile-sheet-panel", panelClassName)}
      >
        <div className="mobile-sheet-header">
          <div className="space-y-1">
            <h2 id={titleId} className="text-base font-semibold text-text-strong">
              {title}
            </h2>
            {description ? (
              <p id={descriptionId} className="text-sm text-text-body">
                {description}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            aria-label={`Close ${title}`}
            className="flex h-10 w-10 items-center justify-center rounded-full text-text-body transition-colors hover:bg-slate-100"
            onClick={() => onOpenChange(false)}
          >
            <span aria-hidden="true" className="text-lg leading-none">
              ×
            </span>
          </button>
        </div>
        <div className="mobile-sheet-body">{children}</div>
        {footer ? <div className="mobile-sheet-footer">{footer}</div> : null}
      </div>
    </div>
  );
}
