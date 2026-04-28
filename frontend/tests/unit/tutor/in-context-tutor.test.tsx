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

function buildDelayedNdjsonResponse(
  status: number,
  chunks: Array<{ chunk: string; delayMs?: number }>,
): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      for (const { chunk, delayMs = 0 } of chunks) {
        if (delayMs > 0) {
          await new Promise((resolve) => setTimeout(resolve, delayMs));
        }
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

    expect(screen.getByText("Đang suy nghĩ...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Lecture not found")).toBeInTheDocument();
    });
    expect(screen.queryByText("...")).not.toBeInTheDocument();
  });

  it("shows a clear loading bubble before the first streamed answer tokens arrive", async () => {
    fetchMock.mockResolvedValue(
      buildChunkedNdjsonResponse(200, [
        '{"a":"First streamed answer."}\n{"qa_id":9}\n',
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
      target: { value: "Start streaming please" },
    });
    fireEvent.click(screen.getAllByRole("button")[1]);

    expect(screen.getByText("Đang suy nghĩ...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("First streamed answer.")).toBeInTheDocument();
    });
  });

  it("parses NDJSON responses even when JSON objects are split across network chunks", async () => {
    fetchMock.mockResolvedValue(
      buildChunkedNdjsonResponse(200, [
        '{"status":"Đang suy nghĩ',
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

  it("shows backend status text separately before streamed answer content arrives", async () => {
    fetchMock.mockResolvedValue(
      buildDelayedNdjsonResponse(200, [
        { chunk: '{"status":"Đang đọc ngữ cảnh bài giảng..."}\n' },
        { chunk: '{"status":"Đang tìm phần nội dung liên quan..."}\n', delayMs: 20 },
        { chunk: '{"a":"Answer starts here."}\n{"qa_id":12}\n', delayMs: 150 },
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
      target: { value: "Explain the context first" },
    });
    fireEvent.click(screen.getAllByRole("button")[1]);

    expect(await screen.findByText("Đang đọc ngữ cảnh bài giảng...")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Đang tìm phần nội dung liên quan...")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText("Answer starts here.")).toBeInTheDocument();
    });
    expect(screen.queryByText("Đang đọc ngữ cảnh bài giảng...")).not.toBeInTheDocument();
    expect(screen.queryByText("Đang tìm phần nội dung liên quan...")).not.toBeInTheDocument();
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

  it("disables input while streaming and restores focus when the reply completes", async () => {
    fetchMock.mockResolvedValue(
      buildDelayedNdjsonResponse(200, [
        { chunk: '{"status":"Đang suy nghĩ..."}\n' },
        { chunk: '{"a":"Done."}\n{"qa_id":14}\n', delayMs: 120 },
      ]),
    );

    render(
      <InContextTutor
        lectureId="cs231n-lecture-1"
        currentTime={120}
        captureFrame={() => null}
        unitTitle="Lecture 1: Introduction"
        onClose={() => {}}
      />,
    );

    const input = screen.getByPlaceholderText("Ask about this lecture...");
    fireEvent.change(input, {
      target: { value: "Tell me more" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    expect(input).toBeDisabled();
    expect(screen.getByRole("button", { name: "Tutor is replying" })).toBeDisabled();

    await waitFor(() => {
      expect(screen.getByText("Done.")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(input).not.toBeDisabled();
      expect(document.activeElement).toBe(input);
    });
  });

  it("shows a step list when the backend emits multiple tutor stages", async () => {
    fetchMock.mockResolvedValue(
      buildDelayedNdjsonResponse(200, [
        { chunk: '{"status":"Đang đọc ngữ cảnh bài giảng..."}\n' },
        { chunk: '{"status":"Đang tìm phần nội dung liên quan..."}\n', delayMs: 20 },
        { chunk: '{"status":"Đang suy nghĩ câu trả lời..."}\n', delayMs: 20 },
        { chunk: '{"a":"Mình đã tổng hợp xong."}\n{"qa_id":18}\n', delayMs: 100 },
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
      target: { value: "Tóm tắt giúp mình" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    expect(await screen.findByText("Đang đọc ngữ cảnh bài giảng...")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Đang tìm phần nội dung liên quan...")).toBeInTheDocument();
      expect(screen.getByText("Đang suy nghĩ câu trả lời...")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText("Mình đã tổng hợp xong.")).toBeInTheDocument();
    });
  });

  it("shows a tool-specific step only when the backend actually uses a tool", async () => {
    fetchMock.mockResolvedValue(
      buildDelayedNdjsonResponse(200, [
        { chunk: '{"status":"Đang suy nghĩ câu trả lời..."}\n' },
        { chunk: '{"status":"Đang kiểm tra phép tính..."}\n', delayMs: 20 },
        { chunk: '{"status":"Đang hoàn thiện câu trả lời..."}\n', delayMs: 20 },
        { chunk: '{"a":"Kết quả đã được kiểm tra."}\n{"qa_id":22}\n', delayMs: 100 },
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
      target: { value: "Tính giúp mình giá trị này" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    expect(await screen.findByText("Đang kiểm tra phép tính...")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Đang hoàn thiện câu trả lời...")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText("Kết quả đã được kiểm tra.")).toBeInTheDocument();
    });
  });
});
