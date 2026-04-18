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

function buildChunkedNdjsonResponse(status: number, chunks: string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });

  return new Response(stream, {
    status,
    headers: { "Content-Type": "application/x-ndjson" },
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

  it("parses NDJSON responses even when JSON objects are split across network chunks", async () => {
    fetchMock.mockResolvedValue(
      buildChunkedNdjsonResponse(200, [
        '{"status":"Thinking',
        '..."}\n{"a":"Measure brain ',
        'activity means "}\n{"a":"recording neural signals."}\n{"qa_id":42}\n',
      ]),
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
      target: { value: "measure brain activity là gì" },
    });
    fireEvent.click(screen.getAllByRole("button")[1]);

    await waitFor(() => {
      expect(
        screen.getByText(/Measure brain activity means recording neural signals\./),
      ).toBeInTheDocument();
    });
  });

  it("includes context_binding_id in tutor requests when provided", async () => {
    fetchMock.mockResolvedValue(
      buildChunkedNdjsonResponse(200, ['{"a":"Bound to unit context."}\n{"qa_id":7}\n']),
    );

    render(
      <InContextTutor
        lectureId="cs231n-lecture-1"
        currentTime={120}
        captureFrame={() => null}
        contextBindingId="ctx_unit_lecture_01"
        unitTitle="Lecture 1: Introduction"
        onClose={() => {}}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("Ask about this lecture..."), {
      target: { value: "Keep this tied to the active unit" },
    });
    fireEvent.click(screen.getAllByRole("button")[1]);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toMatchObject({
      context_binding_id: "ctx_unit_lecture_01",
    });
  });
});
