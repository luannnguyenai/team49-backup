import { beforeEach, describe, expect, it, vi } from "vitest";

const postMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", () => ({
  api: {
    post: postMock,
  },
}));

describe("agent api", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
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
