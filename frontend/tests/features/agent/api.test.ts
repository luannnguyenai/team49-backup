import { beforeEach, describe, expect, it, vi } from "vitest";

const postMock = vi.hoisted(() => vi.fn());
const getMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", () => ({
  api: {
    get: getMock,
    post: postMock,
  },
}));

describe("agent api", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
    getMock.mockReset();
    postMock.mockReset();
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

  it("uses the public backend URL for browser chat requests when configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000/");
    const { AGENT_REQUEST_TIMEOUT_MS, agentApi } = await import("@/features/agent/api");
    postMock.mockResolvedValueOnce({ data: { ok: true } });

    await agentApi.chat({
      message: "find RCNN",
      incomingMessageId: "msg-3",
      traceMode: "summary",
    });

    expect(postMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/agent/chat",
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
});
