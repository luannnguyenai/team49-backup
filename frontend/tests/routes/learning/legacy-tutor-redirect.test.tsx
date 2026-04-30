import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TutorPage from "@/app/tutor/page";

const navigationMock = vi.hoisted(() => ({
  replace: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useRouter: () => navigationMock,
  };
});

describe("legacy tutor redirect", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
  });

  it("redirects legacy /tutor to /agent even when old active context exists", async () => {
    window.sessionStorage.setItem(
      "al_active_learning_unit",
      JSON.stringify({
        courseSlug: "cs231n",
        unitSlug: "lecture-1-introduction",
      }),
    );

    render(<TutorPage />);

    await waitFor(() => {
      expect(navigationMock.replace).toHaveBeenCalledWith("/agent");
    });
  });

  it("redirects legacy /tutor to /agent when no active context exists", async () => {
    render(<TutorPage />);

    await waitFor(() => {
      expect(navigationMock.replace).toHaveBeenCalledWith("/agent");
    });
  });
});
