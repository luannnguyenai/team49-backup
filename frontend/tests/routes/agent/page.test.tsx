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
  unitContext: vi.fn(),
}));

const learningPathApiMock = vi.hoisted(() => ({
  getLearningPath: vi.fn(),
}));

vi.mock("@/features/agent/api", async () => {
  const actual = await vi.importActual<typeof import("@/features/agent/api")>("@/features/agent/api");
  return {
    ...actual,
    agentApi: agentApiMock,
  };
});

vi.mock("@/features/learning-path/api", () => ({
  learningPathApi: learningPathApiMock,
}));

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
    agentApiMock.unitContext.mockResolvedValue({
      canonical_unit_id: "unit-rf",
      course_id: "CS231n",
      unit_name: "Kernels, stride, pooling, and receptive fields",
      summary: "This unit explains CNN kernels, stride, pooling, and receptive fields.",
      quiz_available: true,
      learn_href: "/courses/cs231n/learn/lecture-03-seg4?t=740",
    });
    learningPathApiMock.getLearningPath.mockResolvedValue({
      total_units: 1,
      completed_units: 1,
      in_progress_units: 0,
      items: [
        {
          id: "path-item-1",
          learning_unit_id: "learning-unit-1",
          learning_unit_title: "Kernels, stride, pooling, and receptive fields",
          section_title: "CNN-based Image Classification",
          course_id: "CS231n",
          course_title: "CS231n",
          learn_href: "/courses/cs231n/learn/lecture-03-seg4?t=740",
          action: "standard_learn",
          estimated_hours: 0.25,
          order_index: 1,
          week_number: 3,
          status: "completed",
          canonical_unit_id: "unit-rf",
        },
      ],
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

  it("opens source details from the citation card and hides duplicate open-unit actions", async () => {
    agentApiMock.chat.mockResolvedValueOnce({
      conversationId: "conversation-1",
      messageId: "message-source",
      answer: {
        markdown: "I found a source for receptive fields.",
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
      actions: [
        {
          type: "open_unit",
          label: "Open duplicate unit action",
          canonical_unit_id: "unit-rf",
          learn_href: "/courses/cs231n/learn/lecture-03-seg4?t=740",
        },
      ],
      warning: null,
    });
    render(<AgentPage />);

    const promptButtons = await screen.findAllByRole("button", { name: /where should i review cnns/i });
    fireEvent.click(promptButtons[0]);

    const source = await screen.findByRole("button", {
      name: /view source details: kernels, stride, pooling, and receptive fields/i,
    });
    expect(screen.queryByText("Open duplicate unit action")).not.toBeInTheDocument();
    fireEvent.click(source);

    await waitFor(() => {
      expect(agentApiMock.unitContext).toHaveBeenCalledWith("unit-rf");
      expect(learningPathApiMock.getLearningPath).toHaveBeenCalled();
    });
    expect(await screen.findAllByText("Source detail")).toHaveLength(2);
    expect(screen.getByTestId("agent-source-sidebar")).toHaveClass("hidden", "md:block");
    expect(screen.getByTestId("agent-source-sidebar")).not.toHaveClass("fixed");
    expect(screen.getByTestId("agent-source-drawer")).toHaveClass("fixed", "md:hidden");
    expect(screen.getAllByText("Completed").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/This unit explains CNN kernels/i).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: /start learning/i })[0]).toHaveAttribute(
      "href",
      "/courses/cs231n/learn/lecture-03-seg4?t=740",
    );
  });

  it("cleans timestamp markers from source detail summaries", async () => {
    agentApiMock.unitContext.mockResolvedValueOnce({
      canonical_unit_id: "unit-rf",
      course_id: "CS231n",
      unit_name: "Kernels, stride, pooling, and receptive fields",
      summary: "CNNs are introduced as image models [ts=1397s] and trained end-to-end [ts=1420s].",
      quiz_available: true,
      learn_href: "/courses/cs231n/learn/lecture-03-seg4?t=740",
    });
    render(<AgentPage />);

    const promptButtons = await screen.findAllByRole("button", { name: /where should i review cnns/i });
    fireEvent.click(promptButtons[0]);
    fireEvent.click(
      await screen.findByRole("button", {
        name: /view source details: kernels, stride, pooling, and receptive fields/i,
      }),
    );

    expect(await screen.findAllByText(/CNNs are introduced as image models and trained end-to-end/i)).toHaveLength(2);
    expect(screen.queryByText(/\[ts=\d+s\]/)).not.toBeInTheDocument();
  });

  it("does not render model-generated markdown links as navigation", async () => {
    agentApiMock.chat.mockResolvedValueOnce({
      conversationId: "conversation-1",
      messageId: "message-external-link",
      answer: {
        markdown:
          "See [Lecture 5](https://www.coursera.org/learn/example) or [source](/courses/cs231n/learn/lecture-5-seg3) for CNN details.",
        confidence: "grounded",
      },
      citations: [],
      actions: [],
      warning: null,
    });
    render(<AgentPage />);

    const input = await screen.findByPlaceholderText("Message AI Assistant...");
    fireEvent.change(input, { target: { value: "nền tảng CNN" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByText("Lecture 5")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /lecture 5/i })).not.toBeInTheDocument();
    expect(screen.getByText("source")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /source/i })).not.toBeInTheDocument();
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

  it("retries server-side agent fallback responses with the same message id", async () => {
    agentApiMock.chat
      .mockResolvedValueOnce({
        conversationId: "conversation-1",
        messageId: "message-server-fallback",
        answer: {
          markdown:
            "The AI assistant is temporarily unavailable due to a system incident. Please try again later. Error code: AGENT_LLM_UNAVAILABLE.",
          confidence: "fallback",
        },
        citations: [],
        actions: [],
        warning: {
          type: "agent_unavailable",
          message: "AGENT_LLM_UNAVAILABLE",
        },
        fallback: {
          reason: "agent_unavailable",
          message: "The agent request failed before a safe answer could be produced.",
          errorCode: "AGENT_LLM_UNAVAILABLE",
        },
      })
      .mockResolvedValueOnce({
        conversationId: "conversation-1",
        messageId: "message-server-retry",
        answer: {
          markdown: "Retry found CNN application content.",
          confidence: "grounded",
        },
        citations: [],
        actions: [],
        warning: null,
      });
    render(<AgentPage />);

    const input = await screen.findByPlaceholderText("Message AI Assistant...");
    fireEvent.change(input, { target: { value: "thế còn CNN ứng dụng thì sao" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    const retry = await screen.findByRole("button", { name: /retry/i });
    const firstCall = agentApiMock.chat.mock.calls[0][0];
    fireEvent.click(retry);

    await waitFor(() => {
      expect(agentApiMock.chat).toHaveBeenCalledTimes(2);
    });
    expect(agentApiMock.chat.mock.calls[1][0]).toMatchObject({
      message: "thế còn CNN ứng dụng thì sao",
      incomingMessageId: firstCall.incomingMessageId,
    });
    expect(await screen.findByText("Retry found CNN application content.")).toBeInTheDocument();
  });

  it("labels client-side agent timeouts separately from network failures", async () => {
    agentApiMock.chat.mockRejectedValueOnce(
      Object.assign(new Error("timeout of 15000ms exceeded"), { code: "ECONNABORTED" }),
    );
    render(<AgentPage />);

    const input = await screen.findByPlaceholderText("Message AI Assistant...");
    fireEvent.change(input, { target: { value: "có thể tìm RCNN không" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findAllByText(/AGENT_REQUEST_TIMEOUT/)).toHaveLength(2);
    expect(screen.queryByText(/AGENT_NETWORK_ERROR/)).not.toBeInTheDocument();
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
