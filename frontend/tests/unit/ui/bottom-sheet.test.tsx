import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import BottomSheet from "@/components/ui/BottomSheet";

describe("BottomSheet", () => {
  it("renders a dialog shell when open and closes on backdrop press", () => {
    const onOpenChange = vi.fn();

    render(
      <BottomSheet open onOpenChange={onOpenChange} title="Mobile menu">
        <div>Sheet content</div>
      </BottomSheet>,
    );

    expect(screen.getByRole("dialog", { name: "Mobile menu" })).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("bottom-sheet-backdrop"));

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("restores focus to the trigger when the sheet closes", () => {
    const onOpenChange = vi.fn();

    function Harness({ open }: { open: boolean }) {
      return (
        <>
          <button type="button">Open tools</button>
          <BottomSheet open={open} onOpenChange={onOpenChange} title="Study tools">
            <button type="button">First action</button>
          </BottomSheet>
        </>
      );
    }

    const { rerender } = render(<Harness open />);
    const trigger = screen.getByRole("button", { name: "Open tools" });
    trigger.focus();

    expect(screen.getByRole("dialog", { name: "Study tools" })).toBeInTheDocument();

    rerender(<Harness open={false} />);

    expect(document.activeElement).toBe(trigger);
  });
});
