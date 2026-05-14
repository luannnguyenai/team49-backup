import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import MobileSearchSheet from "@/components/layout/MobileSearchSheet";

const routerPushMock = vi.fn();
const catalogLoaderMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: routerPushMock,
  }),
}));

vi.mock("@/lib/course-catalog-cache", () => ({
  getCachedAllCourseCatalog: (...args: unknown[]) => catalogLoaderMock(...args),
}));

describe("MobileSearchSheet", () => {
  it("loads the catalog when opened and routes to a selected course", async () => {
    const onOpenChange = vi.fn();
    catalogLoaderMock.mockResolvedValue({
      items: [
        {
          id: "cs231n",
          slug: "cs231n",
          title: "CS231n: Deep Learning for Computer Vision",
          short_description: "Deep learning foundations for computer vision.",
          hero_kicker: "Computer Vision",
          is_recommended: true,
          status: "published",
        },
      ],
    });

    render(<MobileSearchSheet open onOpenChange={onOpenChange} />);

    await waitFor(() => {
      expect(catalogLoaderMock).toHaveBeenCalledWith(true, "public");
    });

    fireEvent.change(screen.getByRole("textbox", { name: "Search courses" }), {
      target: { value: "vision" },
    });

    fireEvent.click(
      await screen.findByRole("button", {
        name: /cs231n: deep learning for computer vision/i,
      }),
    );

    expect(routerPushMock).toHaveBeenCalledWith("/courses/cs231n");
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
