import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TutorPage from "@/app/tutor/page";

const navigationMock = vi.hoisted(() => ({
  replace: vi.fn(),
}));

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useRouter: () => navigationMock,
  };
});

describe("legacy tutor route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("redirects to the AI Assistant route", async () => {
    render(<TutorPage />);

    expect(screen.getByText(/redirecting to ai assistant/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(navigationMock.replace).toHaveBeenCalledWith("/agent");
    });
  });
});
