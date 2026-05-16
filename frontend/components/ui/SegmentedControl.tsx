"use client";

import { cn } from "@/lib/utils";

type SegmentedControlOption<T extends string> = {
  label: string;
  value: T;
  disabled?: boolean;
};

type SegmentedControlProps<T extends string> = {
  ariaLabel: string;
  value: T;
  onChange: (value: T) => void;
  options: SegmentedControlOption<T>[];
  className?: string;
};

export default function SegmentedControl<T extends string>({
  ariaLabel,
  value,
  onChange,
  options,
  className,
}: SegmentedControlProps<T>) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        "inline-flex min-w-0 items-center gap-1 rounded-full border border-[color:var(--border-subtle)] bg-[color:var(--surface-elevated)] p-1 shadow-sm",
        className,
      )}
    >
      {options.map((option) => {
        const active = option.value === value;

        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={active}
            aria-disabled={option.disabled || undefined}
            disabled={option.disabled}
            className={cn(
              "min-w-0 rounded-full px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-[color:var(--brand-ink)] text-[color:var(--brand-ink-fg)]"
                : "text-text-body hover:bg-slate-100",
            )}
            onClick={() => {
              if (!active && !option.disabled) {
                onChange(option.value);
              }
            }}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
