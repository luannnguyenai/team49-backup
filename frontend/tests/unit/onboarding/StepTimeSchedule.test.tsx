import { render, screen } from "@testing-library/react";
import { useForm } from "react-hook-form";
import { describe, expect, it } from "vitest";
import StepTimeSchedule from "@/components/onboarding/StepTimeSchedule";
import type { OnboardingFormData } from "@/lib/onboarding-schema";

function Harness() {
  const form = useForm<OnboardingFormData>({
    defaultValues: {
      available_hours_per_week: 5,
      target_deadline: "2026-05-01",
      preferred_method: "video",
    },
  });

  return (
    <StepTimeSchedule
      register={form.register}
      errors={form.formState.errors}
      watch={form.watch}
    />
  );
}

describe("StepTimeSchedule", () => {
  it("collects pacing inputs without showing a misleading completion estimate", () => {
    render(<Harness />);

    expect(screen.getByText("Bạn có thể dành bao nhiêu giờ/tuần?")).toBeInTheDocument();
    expect(screen.getByText("Bạn muốn hoàn thành trước ngày nào?")).toBeInTheDocument();
    expect(screen.queryByText("Dự kiến hoàn thành")).not.toBeInTheDocument();
  });
});
