import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AgentPage from "@/app/agent/page";

const agentApiMock = vi.hoisted(() => ({
  listConversations: vi.fn(),
  createConversation: vi.fn(),
  messages: vi.fn(),
  memory: vi.fn(),
  chat: vi.fn(),
  continueAction: vi.fn(),
  startAssessmentWorkflow: vi.fn(),
  resumeAssessmentWorkflow: vi.fn(),
  startAssessmentAction: vi.fn(),
}));

vi.mock("@/features/agent/api", async () => {
  const actual = await vi.importActual<typeof import("@/features/agent/api")>("@/features/agent/api");
  return {
    ...actual,
    agentApi: agentApiMock,
  };
});

vi.mock("@/stores/authStore", () => ({
  useAuthStore: () => ({
    user: {
      id: "user-1",
      full_name: "Test Learner",
      is_onboarded: true,
    },
  }),
}));

describe("agent page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window.HTMLElement.prototype, "scrollTo", {
      configurable: true,
      value: vi.fn(),
    });
    agentApiMock.listConversations.mockResolvedValue([]);
    agentApiMock.messages.mockResolvedValue([]);
    agentApiMock.chat.mockResolvedValue({
      conversationId: "conversation-1",
      messageId: "message-1",
      answer: {
        markdown: "Receptive fields are covered in CS231n.",
        confidence: "grounded",
      },
      citations: [
        {
          canonical_unit_id: "unit-rf",
          course_id: "CS231n",
          unit_name: "Kernels, stride, pooling, and receptive fields",
          lecture_title: "CNN-based Image Classification",
          learn_href: "/courses/cs231n/learn/lecture-03-seg4?t=740",
          source: "summary",
        },
      ],
      actions: [],
      warning: null,
    });
  });

  it("renders empty assistant state when there is no active conversation", async () => {
    render(<AgentPage />);

    expect(await screen.findAllByRole("heading", { name: "AI Assistant" })).toHaveLength(2);
    expect(screen.getByText(/ask about concepts, prerequisites/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /where should i review cnns/i })).toHaveLength(2);
  });

  it("keeps the chat workspace focused without the context sidebar or header clear action", async () => {
    render(<AgentPage />);

    expect(await screen.findAllByRole("heading", { name: "AI Assistant" })).toHaveLength(2);
    expect(screen.queryByText(/thread memory/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/current path first/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/clear current chat/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/open context panel/i)).not.toBeInTheDocument();
  });

  it("sends a chat message and renders answer citations", async () => {
    render(<AgentPage />);

    const promptButtons = await screen.findAllByRole("button", { name: /where should i review cnns/i });
    fireEvent.click(promptButtons[0]);

    await waitFor(() => {
      expect(agentApiMock.chat).toHaveBeenCalledWith({
        message: "Where should I review CNNs?",
        incomingMessageId: expect.any(String),
        conversationId: null,
        traceMode: "summary",
      });
    });

    expect(await screen.findByText("Receptive fields are covered in CS231n.")).toBeInTheDocument();
    expect(screen.getByText("Kernels, stride, pooling, and receptive fields")).toBeInTheDocument();
  });

  it("renders assistant markdown and retries a failed request with the same message id", async () => {
    agentApiMock.chat
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValueOnce({
        conversationId: "conversation-1",
        messageId: "message-retry",
        answer: {
          markdown: "Retry found **U-Net** content.",
          confidence: "grounded",
        },
        citations: [],
        actions: [],
        warning: null,
      });
    render(<AgentPage />);

    const input = await screen.findByPlaceholderText("Message AI Assistant...");
    fireEvent.change(input, { target: { value: "kiểm cho tôi thông tin về UNet" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    const retry = await screen.findByRole("button", { name: /retry/i });
    const firstCall = agentApiMock.chat.mock.calls[0][0];
    fireEvent.click(retry);

    await waitFor(() => {
      expect(agentApiMock.chat).toHaveBeenCalledTimes(2);
    });
    expect(agentApiMock.chat.mock.calls[1][0]).toMatchObject({
      message: "kiểm cho tôi thông tin về UNet",
      incomingMessageId: firstCall.incomingMessageId,
    });
    const strong = await screen.findByText("U-Net");
    expect(strong.tagName).toBe("STRONG");
  });

  it("continues a pending action with a stable action id", async () => {
    agentApiMock.chat.mockResolvedValueOnce({
      conversationId: "conversation-1",
      messageId: "message-action",
      answer: {
        markdown: "I can replan after you confirm.",
        confidence: "partial",
      },
      citations: [],
      actions: [
        {
          type: "request_replan",
          label: "Confirm replan",
          actionId: "act-1",
          status: "awaiting_confirmation",
        },
      ],
      warning: null,
    });
    agentApiMock.continueAction.mockResolvedValueOnce({
      conversationId: "conversation-1",
      messageId: "message-commit",
      answer: {
        markdown: "I recalculated your learning plan from the latest assessment evidence.",
        confidence: "partial",
      },
      citations: [],
      actions: [],
      warning: null,
    });
    render(<AgentPage />);

    const promptButtons = await screen.findAllByRole("button", { name: /where should i review cnns/i });
    fireEvent.click(promptButtons[0]);
    const confirm = await screen.findByRole("button", { name: /confirm replan/i });
    fireEvent.click(confirm);

    await waitFor(() => {
      expect(agentApiMock.continueAction).toHaveBeenCalledWith({
        conversationId: "conversation-1",
        actionId: "act-1",
        decision: "approve",
        incomingMessageId: expect.any(String),
      });
    });
    expect(await screen.findByText("I recalculated your learning plan from the latest assessment evidence.")).toBeInTheDocument();
  });

  it("chooses a target path card through the active conversation", async () => {
    agentApiMock.chat
      .mockResolvedValueOnce({
        conversationId: "conversation-1",
        messageId: "message-path-choice",
        answer: {
          markdown: "I found CNN in multiple paths. Which path do you want?",
          confidence: "partial",
        },
        citations: [],
        actions: [
          {
            type: "choose_target_path",
            label: "CNNs in Computer Vision",
            workflowId: "computer_vision",
          },
        ],
        warning: null,
      })
      .mockResolvedValueOnce({
        conversationId: "conversation-1",
        messageId: "message-cv-results",
        answer: {
          markdown: "I found relevant CNN units in Computer Vision.",
          confidence: "grounded",
        },
        citations: [],
        actions: [],
        warning: null,
      });
    render(<AgentPage />);

    const promptButtons = await screen.findAllByRole("button", { name: /where should i review cnns/i });
    fireEvent.click(promptButtons[0]);
    const pathChoice = await screen.findByRole("button", { name: /cnns in computer vision/i });
    fireEvent.click(pathChoice);

    await waitFor(() => {
      expect(agentApiMock.chat).toHaveBeenLastCalledWith({
        message: "choose_path:computer_vision",
        incomingMessageId: expect.any(String),
        conversationId: "conversation-1",
        traceMode: "summary",
      });
    });
    expect(await screen.findByText("I found relevant CNN units in Computer Vision.")).toBeInTheDocument();
  });
});
