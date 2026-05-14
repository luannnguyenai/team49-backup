import { beforeEach, describe, expect, it, vi } from "vitest";

const postMock = vi.hoisted(() => vi.fn());
const getMock = vi.hoisted(() => vi.fn());
const refreshAccessTokenMock = vi.hoisted(() => vi.fn());
const tokenStorageMock = vi.hoisted(() => ({
  getAccess: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: {
    get: getMock,
    post: postMock,
  },
  refreshAccessToken: refreshAccessTokenMock,
  tokenStorage: tokenStorageMock,
}));

describe("agent api", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    getMock.mockReset();
    postMock.mockReset();
    refreshAccessTokenMock.mockReset();
    tokenStorageMock.getAccess.mockReset();
  });

  it("uses an agent-specific timeout for chat requests", async () => {
    const { AGENT_REQUEST_TIMEOUT_MS, agentApi } = await import("@/features/agent/api");
    postMock.mockResolvedValueOnce({ data: { ok: true } });

    await agentApi.chat({
      message: "find RCNN",
      incomingMessageId: "msg-1",
      traceMode: "summary",
    });

    expect(postMock).toHaveBeenCalledWith(
      "/api/agent/chat",
      {
        message: "find RCNN",
        incomingMessageId: "msg-1",
        traceMode: "summary",
      },
      { timeout: AGENT_REQUEST_TIMEOUT_MS },
    );
  });

  it("falls back to the same-origin proxy for browser chat requests when the public backend URL is cross-origin", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://api.example.com/");
    const { AGENT_REQUEST_TIMEOUT_MS, agentApi } = await import("@/features/agent/api");
    postMock.mockResolvedValueOnce({ data: { ok: true } });

    await agentApi.chat({
      message: "find RCNN",
      incomingMessageId: "msg-3",
      traceMode: "summary",
    });

    expect(postMock).toHaveBeenCalledWith(
      "/api/agent/chat",
      {
        message: "find RCNN",
        incomingMessageId: "msg-3",
        traceMode: "summary",
      },
      { timeout: AGENT_REQUEST_TIMEOUT_MS },
    );
  });

  it("passes the selected agent tool mode through chat requests", async () => {
    const { AGENT_REQUEST_TIMEOUT_MS, agentApi } = await import("@/features/agent/api");
    postMock.mockResolvedValueOnce({ data: { ok: true } });

    await agentApi.chat({
      message: "find recent papers about diffusion",
      incomingMessageId: "msg-web-papers",
      traceMode: "summary",
      toolMode: "web_papers",
    });

    expect(postMock).toHaveBeenCalledWith(
      "/api/agent/chat",
      {
        message: "find recent papers about diffusion",
        incomingMessageId: "msg-web-papers",
        traceMode: "summary",
        toolMode: "web_papers",
      },
      { timeout: AGENT_REQUEST_TIMEOUT_MS },
    );
  });

  it("passes the selected chat model through chat requests", async () => {
    const { AGENT_REQUEST_TIMEOUT_MS, agentApi } = await import("@/features/agent/api");
    postMock.mockResolvedValueOnce({ data: { ok: true } });

    await agentApi.chat({
      message: "explain CNNs",
      incomingMessageId: "msg-qwen",
      traceMode: "summary",
      chatModelId: "qwen35_4b",
    });

    expect(postMock).toHaveBeenCalledWith(
      "/api/agent/chat",
      {
        message: "explain CNNs",
        incomingMessageId: "msg-qwen",
        traceMode: "summary",
        chatModelId: "qwen35_4b",
      },
      { timeout: AGENT_REQUEST_TIMEOUT_MS },
    );
  });

  it("loads chat model availability from the shared safe endpoint", async () => {
    const { agentApi } = await import("@/features/agent/api");
    getMock.mockResolvedValueOnce({
      data: {
        models: [
          { id: "default", label: "Default", status: "healthy", available: true },
          { id: "qwen35_4b", label: "Qwen 3.5 4B", status: "down", available: false },
        ],
      },
    });

    const result = await agentApi.modelAvailability();

    expect(getMock).toHaveBeenCalledWith("/api/chat-models/availability");
    expect(result.models[1]).toMatchObject({
      id: "qwen35_4b",
      status: "down",
      available: false,
    });
  });

  it("uses an agent-specific timeout for action continuations", async () => {
    const { AGENT_REQUEST_TIMEOUT_MS, agentApi } = await import("@/features/agent/api");
    postMock.mockResolvedValueOnce({ data: { ok: true } });

    await agentApi.continueAction({
      conversationId: "conversation-1",
      actionId: "action-1",
      decision: "approve",
      incomingMessageId: "msg-2",
    });

    expect(postMock).toHaveBeenCalledWith(
      "/api/agent/actions/continue",
      {
        conversationId: "conversation-1",
        actionId: "action-1",
        decision: "approve",
        incomingMessageId: "msg-2",
      },
      { timeout: AGENT_REQUEST_TIMEOUT_MS },
    );
  });

  it("refreshes and retries streaming chat once after a 401", async () => {
    const firstResponse = new Response("", { status: 401 });
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('{"done":{"conversationId":"conversation-1","messageId":"message-1","answer":{"markdown":"ok","confidence":"partial"},"citations":[],"actions":[]}}\n'));
        controller.close();
      },
    });
    const secondResponse = new Response(stream, { status: 200 });
    const fetchMock = vi.fn().mockResolvedValueOnce(firstResponse).mockResolvedValueOnce(secondResponse);
    vi.stubGlobal("fetch", fetchMock);
    tokenStorageMock.getAccess.mockReturnValueOnce("expired-token").mockReturnValueOnce("fresh-token");
    refreshAccessTokenMock.mockResolvedValueOnce("fresh-token");

    const { agentApi } = await import("@/features/agent/api");
    const events = [];
    const responseStream = await agentApi.chatStream({
      message: "Send me replan link",
      incomingMessageId: "msg-1",
      traceMode: "summary",
    });
    for await (const event of responseStream) {
      events.push(event);
    }

    expect(refreshAccessTokenMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][1]?.headers).toMatchObject({ Authorization: "Bearer expired-token" });
    expect(fetchMock.mock.calls[1][1]?.headers).toMatchObject({ Authorization: "Bearer fresh-token" });
    expect(events).toEqual([
      {
        done: {
          conversationId: "conversation-1",
          messageId: "message-1",
          answer: { markdown: "ok", confidence: "partial" },
          citations: [],
          actions: [],
        },
      },
    ]);
  });

  it("keeps streaming chat on the same-origin proxy when NEXT_PUBLIC_API_URL is cross-origin", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://api.example.com/");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          new ReadableStream({
            start(controller) {
              controller.enqueue(
                new TextEncoder().encode(
                  '{"done":{"conversationId":"conversation-1","messageId":"message-1","answer":{"markdown":"ok","confidence":"partial"},"citations":[],"actions":[]}}\n',
                ),
              );
              controller.close();
            },
          }),
          { status: 200 },
        ),
      ),
    );

    const { agentApi } = await import("@/features/agent/api");
    const responseStream = await agentApi.chatStream({
      message: "stream over same origin",
      incomingMessageId: "msg-stream-origin",
      traceMode: "summary",
    });

    for await (const _event of responseStream) {
      // Drain stream.
    }

    const fetchMock = vi.mocked(fetch);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/agent/chat/stream",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
  });
});
