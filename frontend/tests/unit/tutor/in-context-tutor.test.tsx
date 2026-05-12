import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import InContextTutor from "@/components/learn/InContextTutor";
import {
  TUTOR_SESSION_HISTORY_STORAGE_KEY,
  buildTutorConversationKey,
} from "@/lib/tutorSessionHistory";

vi.mock("@/stores/authStore", () => ({
  useAuthStore: (selector?: (state: unknown) => unknown) => {
    const state = {
      user: {
        id: "user-1",
        email: "learner@example.com",
        full_name: "Learner Example",
        available_hours_per_week: null,
        target_deadline: null,
        preferred_method: null,
        is_onboarded: true,
        created_at: "2026-05-02T14:05:00.000Z",
      },
    };
    return selector ? selector(state) : state;
  },
}));

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

  function mockTutorFetch(options: {
    askResponse?: Response;
    historyPayload?: unknown;
    modelAvailabilityPayload?: unknown;
  }) {
    fetchMock.mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const method = init?.method ?? (input instanceof Request ? input.method : "GET");

      if (method === "GET" && url.endsWith("/api/chat-models/availability")) {
        return Promise.resolve(
          new Response(
            JSON.stringify(
              options.modelAvailabilityPayload ?? {
                models: [
                  { id: "default", label: "Default", status: "healthy", available: true },
                  { id: "qwen35_4b", label: "Qwen 3.5 4B", status: "healthy", available: true },
                ],
              },
            ),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }

      if (method === "GET" && url.startsWith("/api/lectures/qa-history")) {
        return Promise.resolve(
          new Response(JSON.stringify(options.historyPayload ?? []), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }

      if (method === "POST" && url.endsWith("/api/lectures/ask") && options.askResponse) {
        return Promise.resolve(options.askResponse);
      }

      return Promise.reject(new Error(`Unhandled fetch mock for ${method} ${url}`));
    });
  }

  function getFetchCallsByMethod(method: string) {
    return fetchMock.mock.calls.filter((call) => {
      const [input, init] = call as [string | URL | Request, RequestInit | undefined];
      const requestMethod =
        init?.method ?? (input instanceof Request ? input.method : "GET");
      return requestMethod === method;
    });
  }

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    mockTutorFetch({});
    Element.prototype.scrollIntoView = vi.fn();
    sessionStorage.clear();
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("shows backend error details instead of leaving the AI placeholder hanging", async () => {
    mockTutorFetch({
      askResponse: buildJsonResponse(404, { detail: "Lecture not found" }),
    });

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

    expect(screen.queryByText("Thinking...")).not.toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Lecture not found")).toBeInTheDocument();
    });
    expect(screen.queryByText("...")).not.toBeInTheDocument();
  });

  it("uses the direct backend tutor stream URL when NEXT_PUBLIC_API_URL is configured", async () => {
    const originalApiUrl = process.env.NEXT_PUBLIC_API_URL;
    process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000";

    try {
      mockTutorFetch({
        askResponse: buildChunkedNdjsonResponse(200, ['{"a":"Direct stream response."}\n{"qa_id":88}\n']),
      });

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
        target: { value: "Explain the main idea." },
      });
      fireEvent.click(screen.getAllByRole("button")[1]);

      await waitFor(() => {
        expect(screen.getByText("Direct stream response.")).toBeInTheDocument();
      });

      expect(fetchMock).toHaveBeenCalledWith(
        "http://localhost:8000/api/lectures/ask",
        expect.objectContaining({ method: "POST" }),
      );
    } finally {
      if (originalApiUrl === undefined) {
        delete process.env.NEXT_PUBLIC_API_URL;
      } else {
        process.env.NEXT_PUBLIC_API_URL = originalApiUrl;
      }
    }
  });

  it("passes the selected tutor chat model in ask requests", async () => {
    mockTutorFetch({
      askResponse: buildChunkedNdjsonResponse(200, ['{"a":"Qwen tutor response."}\n{"qa_id":88}\n']),
    });

    render(
      <InContextTutor
        lectureId="cs231n-lecture-1"
        currentTime={840}
        captureFrame={() => null}
        unitTitle="Lecture 1: Introduction"
        onClose={() => {}}
      />,
    );

    fireEvent.change(screen.getByLabelText("Tutor model"), {
      target: { value: "qwen35_4b" },
    });
    fireEvent.change(screen.getByPlaceholderText("Ask about this lecture..."), {
      target: { value: "Explain the slide." },
    });
    fireEvent.click(screen.getAllByRole("button")[1]);

    await waitFor(() => {
      expect(screen.getByText("Qwen tutor response.")).toBeInTheDocument();
    });

    const postCall = getFetchCallsByMethod("POST")[0] as [string | URL | Request, RequestInit | undefined];
    const body = JSON.parse(String(postCall[1]?.body ?? "{}"));
    expect(body.chatModelId).toBe("qwen35_4b");
  });

  it("disables down tutor models and falls back to default before sending", async () => {
    localStorage.setItem("tutor.chatModelId", "qwen35_4b");
    mockTutorFetch({
      modelAvailabilityPayload: {
        models: [
          { id: "default", label: "Default", status: "healthy", available: true },
          { id: "qwen35_4b", label: "Qwen 3.5 4B", status: "down", available: false },
        ],
      },
      askResponse: buildChunkedNdjsonResponse(200, ['{"a":"Default tutor response."}\n{"qa_id":89}\n']),
    });

    render(
      <InContextTutor
        lectureId="cs231n-lecture-1"
        currentTime={840}
        captureFrame={() => null}
        unitTitle="Lecture 1: Introduction"
        onClose={() => {}}
      />,
    );

    const modelSelect = screen.getByLabelText("Tutor model");
    await waitFor(() => {
      expect(modelSelect).toHaveValue("default");
    });
    expect(screen.getByRole("option", { name: /qwen 3.5 4b.*down/i })).toBeDisabled();

    fireEvent.change(screen.getByPlaceholderText("Ask about this lecture..."), {
      target: { value: "Explain the slide." },
    });
    fireEvent.click(screen.getAllByRole("button")[1]);

    await waitFor(() => {
      expect(screen.getByText("Default tutor response.")).toBeInTheDocument();
    });

    const postCall = getFetchCallsByMethod("POST")[0] as [string | URL | Request, RequestInit | undefined];
    const body = JSON.parse(String(postCall[1]?.body ?? "{}"));
    expect(body.chatModelId).toBe("default");
    expect(localStorage.getItem("tutor.chatModelId")).toBe("default");
  });

  it("hydrates saved chat history from session storage on mount", async () => {
    sessionStorage.setItem(
      TUTOR_SESSION_HISTORY_STORAGE_KEY,
      JSON.stringify({
        [buildTutorConversationKey("cs231n-lecture-1", "ctx_unit_lecture_01")]: [
          {
            id: 71,
            role: "user",
            content: "What did we ask earlier?",
            senderName: "Learner Example",
            sentAt: "21:15",
          },
          {
            id: 71,
            role: "ai",
            content: "You asked about the earlier concept.",
            senderName: "AI Tutor",
            sentAt: "21:15",
            rating: 1,
          },
        ],
      }),
    );

    render(
      <InContextTutor
        lectureId="cs231n-lecture-1"
        currentTime={840}
        captureFrame={() => null}
        contextBindingId="ctx_unit_lecture_01"
        unitTitle="Lecture 1: Introduction"
        onClose={() => {}}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("What did we ask earlier?")).toBeInTheDocument();
      expect(screen.getByText("You asked about the earlier concept.")).toBeInTheDocument();
    });
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/lectures/qa-history"),
      expect.anything(),
    );
  });

  it("restores the previous conversation when the user switches lessons and comes back", async () => {
    mockTutorFetch({
      askResponse: buildChunkedNdjsonResponse(200, ['{"a":"Fresh live answer."}\n{"qa_id":77}\n']),
    });

    const { rerender } = render(
      <InContextTutor
        lectureId="cs231n-lecture-1"
        currentTime={840}
        captureFrame={() => null}
        unitTitle="Lecture 1: Introduction"
        onClose={() => {}}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("Ask about this lecture..."), {
      target: { value: "New question" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    await waitFor(() => {
      expect(screen.getByText("Fresh live answer.")).toBeInTheDocument();
    });

    rerender(
      <InContextTutor
        lectureId="cs231n-lecture-2"
        currentTime={120}
        captureFrame={() => null}
        unitTitle="Lecture 2: Convolutions"
        onClose={() => {}}
      />,
    );

    await waitFor(() => {
      expect(screen.queryByText("New question")).not.toBeInTheDocument();
      expect(screen.queryByText("Fresh live answer.")).not.toBeInTheDocument();
      expect(screen.getByText("Ask anything about this lecture")).toBeInTheDocument();
    });

    rerender(
      <InContextTutor
        lectureId="cs231n-lecture-1"
        currentTime={840}
        captureFrame={() => null}
        unitTitle="Lecture 1: Introduction"
        onClose={() => {}}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("New question")).toBeInTheDocument();
      expect(screen.getByText("Fresh live answer.")).toBeInTheDocument();
    });
  });

  it("shows sender names and timestamps for user and AI messages", async () => {
    mockTutorFetch({
      askResponse: buildChunkedNdjsonResponse(200, [
        '{"a":"Hello from the tutor."}\n{"qa_id":31}\n',
      ]),
    });

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
      target: { value: "What is this lecture about?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    expect(screen.getByText("Learner Example")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getAllByText("AI Tutor").length).toBeGreaterThanOrEqual(2);
      expect(screen.getByText("Hello from the tutor.")).toBeInTheDocument();
    });

    const timestamps = screen.getAllByText(/^\d{2}:\d{2}$/);
    expect(timestamps.length).toBeGreaterThanOrEqual(2);
  });

  it("shows a visible status before the answer even when status and answer arrive in the same chunk", async () => {
    mockTutorFetch({
      askResponse: buildChunkedNdjsonResponse(200, [
        '{"status":"Reading lecture context..."}\n{"a":"Immediate answer."}\n{"qa_id":44}\n',
      ]),
    });

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
      target: { value: "Why do I not see the status?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    expect(await screen.findByText("Reading lecture context...")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Immediate answer.")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "View progress" })).toBeInTheDocument();
  });

  it("shows starter suggestions before the first message and hides them after chat begins", async () => {
    mockTutorFetch({
      askResponse: buildChunkedNdjsonResponse(200, [
        '{"a":"Starter answer."}\n{"qa_id":55}\n',
      ]),
    });

    render(
      <InContextTutor
        lectureId="cs231n-lecture-1"
        currentTime={840}
        captureFrame={() => null}
        unitTitle="Lecture 1: Introduction"
        onClose={() => {}}
        suggestions={[
          "Explain the concept in this section",
          "Why does this topic matter?",
        ]}
      />,
    );

    expect(screen.getByRole("button", { name: "Explain the concept in this section" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Why does this topic matter?" })).not.toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Ask about this lecture..."), {
      target: { value: "Tell me the key idea" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    await waitFor(() => {
      expect(screen.getByText("Starter answer.")).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: "Explain the concept in this section" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Why does this topic matter?" })).not.toBeInTheDocument();
  });

  it("does not show a placeholder status before the backend emits one", async () => {
    mockTutorFetch({
      askResponse: buildChunkedNdjsonResponse(200, [
        '{"a":"First streamed answer."}\n{"qa_id":9}\n',
      ]),
    });

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

    expect(screen.queryByText("Thinking...")).not.toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("First streamed answer.")).toBeInTheDocument();
    });
  });

  it("parses NDJSON responses even when JSON objects are split across network chunks", async () => {
    mockTutorFetch({
      askResponse: buildChunkedNdjsonResponse(200, [
        '{"status":"Thinking',
        '..."}\n{"a":"Measure brain ',
        'activity means "}\n{"a":"recording neural signals."}\n{"qa_id":42}\n',
      ]),
    });

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
    mockTutorFetch({
      askResponse: buildDelayedNdjsonResponse(200, [
        { chunk: '{"status":"Reading lecture context..."}\n' },
        { chunk: '{"status":"Finding the most relevant section..."}\n', delayMs: 20 },
        { chunk: '{"a":"Answer starts here."}\n{"qa_id":12}\n', delayMs: 150 },
      ]),
    });

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

    expect(await screen.findByText("Reading lecture context...")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Finding the most relevant section...")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText("Answer starts here.")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "View progress" })).toBeInTheDocument();
  });

  it("includes context_binding_id in tutor requests when provided", async () => {
    mockTutorFetch({
      askResponse: buildChunkedNdjsonResponse(200, ['{"a":"Bound to unit context."}\n{"qa_id":7}\n']),
    });

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
      expect(getFetchCallsByMethod("POST")).toHaveLength(1);
    });

    const [, init] = getFetchCallsByMethod("POST")[0] as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toMatchObject({
      context_binding_id: "ctx_unit_lecture_01",
    });
  });

  it("disables input while streaming and restores focus when the reply completes", async () => {
    mockTutorFetch({
      askResponse: buildDelayedNdjsonResponse(200, [
        { chunk: '{"status":"Thinking..."}\n' },
        { chunk: '{"a":"Done."}\n{"qa_id":14}\n', delayMs: 120 },
      ]),
    });

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
    await expect(screen.findByText("Thinking...")).resolves.toBeTruthy();

    await waitFor(() => {
      expect(screen.getByText("Done.")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(input).not.toBeDisabled();
      expect(document.activeElement).toBe(input);
    });
  });

  it("shows a step list when the backend emits multiple tutor stages", async () => {
    mockTutorFetch({
      askResponse: buildDelayedNdjsonResponse(200, [
        { chunk: '{"status":"Reading lecture context..."}\n' },
        { chunk: '{"status":"Finding the most relevant section..."}\n', delayMs: 20 },
        { chunk: '{"status":"Thinking through the answer..."}\n', delayMs: 20 },
        { chunk: '{"a":"I have finished summarizing it."}\n{"qa_id":18}\n', delayMs: 100 },
      ]),
    });

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
      target: { value: "Please summarize it" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    expect(await screen.findByText("Reading lecture context...")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Thinking through the answer...")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText("I have finished summarizing it.")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "View progress" }));
    expect(screen.getByText("Reading lecture context...")).toBeInTheDocument();
    expect(screen.getByText("Finding the most relevant section...")).toBeInTheDocument();
    expect(screen.getAllByText("Thinking through the answer...").length).toBeGreaterThanOrEqual(1);
  });

  it("shows a tool-specific step only when the backend actually uses a tool", async () => {
    mockTutorFetch({
      askResponse: buildDelayedNdjsonResponse(200, [
        { chunk: '{"status":"Thinking through the answer..."}\n' },
        { chunk: '{"status":"Checking the calculation..."}\n', delayMs: 20 },
        { chunk: '{"status":"Finalizing the answer..."}\n', delayMs: 20 },
        { chunk: '{"a":"The result has been checked."}\n{"qa_id":22}\n', delayMs: 100 },
      ]),
    });

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
      target: { value: "Calculate this value for me" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    expect(await screen.findByText("Checking the calculation...")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Finalizing the answer...")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText("The result has been checked.")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "View progress" }));
    expect(screen.getByText("Checking the calculation...")).toBeInTheDocument();
    expect(screen.getAllByText("Finalizing the answer...").length).toBeGreaterThanOrEqual(1);
  });

  it("keeps tutor progress available after completion and restores it from session storage", async () => {
    sessionStorage.setItem(
      TUTOR_SESSION_HISTORY_STORAGE_KEY,
      JSON.stringify({
        [buildTutorConversationKey("lesson-1")]: [
          {
            id: 81,
            role: "ai",
            content: "Stored answer.",
            senderName: "AI Tutor",
            sentAt: "21:15",
            rating: 1,
            statusSteps: [
              "Đang đọc ngữ cảnh bài giảng...",
              "Đang suy nghĩ câu trả lời...",
            ],
          },
        ],
      }),
    );

    render(
      <InContextTutor
        lessonKey="lesson-1"
        lectureId="cs231n-lecture-1"
        currentTime={840}
        captureFrame={() => null}
        unitTitle="Lecture 1: Introduction"
        onClose={() => {}}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Stored answer.")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "View progress" }));
    expect(screen.getByText("Reading lecture context...")).toBeInTheDocument();
    expect(screen.getAllByText("Thinking through the answer...").length).toBeGreaterThanOrEqual(1);
  });
});
