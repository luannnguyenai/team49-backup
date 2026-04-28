// lib/onboarding-schema.ts
// Shared Zod schema for the onboarding multi-step form.
// Extracted here to avoid circular imports between page.tsx and step components.

import { z } from "zod";

function defaultTargetDeadline(): string {
  const date = new Date();
  date.setMonth(date.getMonth() + 6);
  return date.toISOString().split("T")[0];
}

export const onboardingSchema = z.object({
  goal_ids: z.array(z.string()).default([]),

  known_unit_ids: z.array(z.string()).default([]),

  known_topic_slugs: z.array(z.string()).default([]),

  desired_section_ids: z.array(z.string()).default([]),

  selected_course_ids: z.array(z.string()).default([]),

  available_hours_per_week: z
    .number({ invalid_type_error: "Phải là số" })
    .min(1, "Ít nhất 1 giờ/tuần")
    .max(20, "Tối đa 20 giờ/tuần")
    .default(5),

  target_deadline: z
    .string()
    .min(1, "Vui lòng chọn ngày")
    .refine(
      (d) => new Date(d) > new Date(),
      "Deadline phải sau ngày hôm nay"
    )
    .default(defaultTargetDeadline),

  preferred_method: z.enum(["reading", "video"]).default("video"),
});

export type OnboardingFormData = z.infer<typeof onboardingSchema>;
