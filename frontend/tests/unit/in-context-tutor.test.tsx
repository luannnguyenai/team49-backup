import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import InContextTutor from "@/components/learn/InContextTutor";

function buildJsonResponse(status: number, payload: unknown): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(`${JSON.stringify(payload)}\n`));
      controller.close();
    },
  });

  return new Response(stream, {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("InContextTutor", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("shows backend error details instead of leaving the AI placeholder hanging", async () => {
    fetchMock.mockResolvedValue(
      buildJsonResponse(404, { detail: "Lecture not found" }),
    );

    render(
      <InContextTutor
        lectureId="cs231n-lecture-1"
        currentTime={840}
        captureFrame={() => null}
        unitTitle="Lecture 1: Introduction"
        onClose={() => {}}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("Ask about this lecture..."), {
      target: { value: "What does the basketball mean?" },
    });
    fireEvent.click(screen.getAllByRole("button")[1]);

    await waitFor(() => {
      expect(screen.getByText("Lecture not found")).toBeInTheDocument();
    });
    expect(screen.queryByText("...")).not.toBeInTheDocument();
  });
});
