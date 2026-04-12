// lib/onboarding-schema.ts
// Shared Zod schema for the onboarding multi-step form.
// Extracted here to avoid circular imports between page.tsx and step components.

import { z } from "zod";

export const onboardingSchema = z.object({
  known_topic_ids: z.array(z.string()),

  desired_module_ids: z
    .array(z.string())
    .min(1, "Chọn ít nhất 1 module để tiếp tục"),

  available_hours_per_week: z
    .number({ invalid_type_error: "Phải là số" })
    .min(1, "Ít nhất 1 giờ/tuần")
    .max(20, "Tối đa 20 giờ/tuần"),

  target_deadline: z
    .string()
    .min(1, "Vui lòng chọn ngày")
    .refine(
      (d) => new Date(d) > new Date(),
      "Deadline phải sau ngày hôm nay"
    ),

  preferred_method: z.enum(["reading", "video"], {
    required_error: "Vui lòng chọn phương pháp học",
  }),
});

export type OnboardingFormData = z.infer<typeof onboardingSchema>;
