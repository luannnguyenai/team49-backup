import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AgentPage from "@/app/agent/page";
import { createLearningProfileForPath } from "@/features/learning-path/profile";
import { useLearningPathStore } from "@/features/learning-path/store";

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

const authStoreMock = vi.hoisted(() => ({
  user: {
    id: "user-1",
    full_name: "Test Learner",
    is_onboarded: true,
  } as { id: string; full_name: string; is_onboarded: boolean } | null,
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
    user: authStoreMock.user,
  }),
}));

describe("agent page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authStoreMock.user = {
      id: "user-1",
      full_name: "Test Learner",
      is_onboarded: true,
    };
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
    useLearningPathStore.setState({
      profile: createLearningProfileForPath("computer_vision", {
        weeklyHours: 5,
        source: "manual",
      }),
      previousProfile: null,
      generatedTopologyHash: null,
    });
  });

  it("renders empty assistant state when there is no active conversation", async () => {
    render(<AgentPage />);

    expect(await screen.findAllByRole("heading", { name: "AI Learning Copilot" })).toHaveLength(2);
    expect(screen.getByText(/ask about prerequisites, weak areas/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /where should i review cnns/i })).toHaveLength(2);
  });

  it("keeps the chat workspace focused without the context sidebar or header clear action", async () => {
    render(<AgentPage />);

    expect(await screen.findAllByRole("heading", { name: "AI Learning Copilot" })).toHaveLength(2);
    expect(screen.queryByText(/thread memory/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/current path first/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/clear current chat/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/open context panel/i)).not.toBeInTheDocument();
  });

  it("clears selected agent history and reloads conversations when the authenticated user changes", async () => {
    agentApiMock.listConversations
      .mockResolvedValueOnce([
        {
          conversationId: "conversation-user-1",
          title: "Old user chat",
          preview: "Should not stay visible",
          messageCount: 1,
          updatedAt: "2026-05-01T00:00:00Z",
        },
      ])
      .mockResolvedValueOnce([]);
    agentApiMock.messages.mockResolvedValueOnce([
      {
        id: "message-old-user",
        role: "assistant",
        markdown: "This belongs to user one.",
        createdAt: "2026-05-01T00:00:00Z",
        citations: [],
        actions: [],
        warning: null,
      },
    ]);

    const { rerender } = render(<AgentPage />);

    expect(await screen.findByText("Old user chat")).toBeInTheDocument();
    expect(await screen.findByText("This belongs to user one.")).toBeInTheDocument();

    authStoreMock.user = {
      id: "user-2",
      full_name: "Second Learner",
      is_onboarded: true,
    };
    rerender(<AgentPage />);

    await waitFor(() => {
      expect(agentApiMock.listConversations).toHaveBeenCalledTimes(2);
    });
    expect(screen.queryByText("Old user chat")).not.toBeInTheDocument();
    expect(screen.queryByText("This belongs to user one.")).not.toBeInTheDocument();
    expect(screen.getByText("No chat history yet.")).toBeInTheDocument();
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

  it("renders prerequisite path actions as a learning order card", async () => {
    agentApiMock.chat.mockResolvedValueOnce({
      conversationId: "conversation-1",
      messageId: "message-prereq-path",
      answer: {
        markdown: "Mask R-CNN extends object detection by adding a mask branch.",
        confidence: "grounded",
      },
      citations: [],
      actions: [
        {
          type: "review_prerequisite_path",
          label: "Review prerequisite order",
          canonicalUnitIds: ["unit-prereq", "unit-target"],
          canonicalUnitId: "unit-target",
          prerequisitePath: {
            targetCanonicalUnitId: "unit-target",
            nodes: [
              {
                canonicalUnitId: "unit-prereq",
                unitName: "Object detection foundations",
                role: "prerequisite",
                status: "skipped",
                learnHref: "/courses/cs231n/learn/object-detection",
                reason: "Already handled; included so the learning order is clear.",
              },
              {
                canonicalUnitId: "unit-target",
                unitName: "Instance segmentation with Mask R-CNN",
                role: "target",
                status: "target",
                learnHref: "/courses/cs231n/learn/mask-r-cnn",
                reason: "Current topic.",
              },
            ],
            edges: [
              {
                fromCanonicalUnitId: "unit-prereq",
                toCanonicalUnitId: "unit-target",
                reason: "Object detection -> Mask R-CNN",
              },
            ],
          },
        },
      ],
      warning: null,
    });
    render(<AgentPage />);

    const input = await screen.findByPlaceholderText("Ask about your learning path...");
    fireEvent.change(input, { target: { value: "Explain Mask R-CNN" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByText("Suggested prerequisite order")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Object detection foundations" })).toHaveAttribute(
      "href",
      "/courses/cs231n/learn/object-detection",
    );
    expect(screen.getByRole("link", { name: "Instance segmentation with Mask R-CNN" })).toHaveAttribute(
      "href",
      "/courses/cs231n/learn/mask-r-cnn",
    );
    expect(screen.getByText("Skipped")).toBeInTheDocument();
    expect(screen.getByText("Current topic")).toBeInTheDocument();
    expect(screen.getByText("Already handled; included so the learning order is clear.")).toBeInTheDocument();
  });

  it("shows a compact expandable thinking progress indicator while the assistant responds", async () => {
    let resolveChat!: (value: {
      conversationId: string;
      messageId: string;
      answer: { markdown: string; confidence: "grounded" };
      citations: never[];
      actions: never[];
      warning: null;
    }) => void;
    agentApiMock.chat.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveChat = resolve;
      }),
    );
    render(<AgentPage />);

    const promptButtons = await screen.findAllByRole("button", { name: /where should i review cnns/i });
    fireEvent.click(promptButtons[0]);

    const thinkingToggle = await screen.findByRole("button", { name: /ai is thinking/i });
    expect(thinkingToggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Routing learning intent")).not.toBeInTheDocument();

    fireEvent.click(thinkingToggle);
    expect(thinkingToggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Routing learning intent")).toBeInTheDocument();
    expect(screen.getByText("Reading source evidence")).toBeInTheDocument();
    expect(screen.getByText("Composing grounded answer")).toBeInTheDocument();

    resolveChat({
      conversationId: "conversation-1",
      messageId: "message-thinking",
      answer: {
        markdown: "Here is the grounded answer.",
        confidence: "grounded",
      },
      citations: [],
      actions: [],
      warning: null,
    });

    expect(await screen.findByText("Here is the grounded answer.")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /ai is thinking/i })).not.toBeInTheDocument();
    });
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
    expect(await screen.findAllByText("Evidence")).toHaveLength(2);
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

    const input = await screen.findByPlaceholderText("Ask about your learning path...");
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

    const input = await screen.findByPlaceholderText("Ask about your learning path...");
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

    const input = await screen.findByPlaceholderText("Ask about your learning path...");
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

    const input = await screen.findByPlaceholderText("Ask about your learning path...");
    fireEvent.change(input, { target: { value: "có thể tìm RCNN không" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findAllByText(/AGENT_REQUEST_TIMEOUT/)).toHaveLength(2);
    expect(screen.queryByText(/AGENT_NETWORK_ERROR/)).not.toBeInTheDocument();
  });

  it("continues a pending assessment action with a stable action id", async () => {
    agentApiMock.chat.mockResolvedValueOnce({
      conversationId: "conversation-1",
      messageId: "message-action",
      answer: {
        markdown: "I can prepare an assessment after you confirm.",
        confidence: "partial",
      },
      citations: [],
      actions: [
        {
          type: "start_assessment",
          label: "Confirm assessment",
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
    const confirm = await screen.findByRole("button", { name: /confirm assessment/i });
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

  it("links replan requests to the dedicated scope builder even when the action is pending", async () => {
    agentApiMock.chat.mockResolvedValueOnce({
      conversationId: "conversation-1",
      messageId: "message-replan",
      answer: {
        markdown: "I can help you optimize your plan by verifying what you already know.",
        confidence: "partial",
      },
      citations: [],
      actions: [
        {
          type: "request_replan",
          label: "Confirm replan",
          actionId: "act-replan",
          status: "awaiting_confirmation",
        },
        {
          type: "request_path_switch",
          label: "Change path",
          learn_href: "/learn",
        },
      ],
      warning: null,
    });
    render(<AgentPage />);

    const promptButtons = await screen.findAllByRole("button", { name: /where should i review cnns/i });
    fireEvent.click(promptButtons[0]);

    const optimizePlan = await screen.findByRole("link", { name: /confirm replan/i });
    expect(optimizePlan).toHaveAttribute("href", "/replan?source=agent&returnTo=%2Fagent");
    expect(agentApiMock.continueAction).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: /confirm replan/i })).not.toBeInTheDocument();
  });

  it("renders path-switch requests as a dropdown with confirmation before changing profile", async () => {
    agentApiMock.chat.mockResolvedValueOnce({
      conversationId: "conversation-1",
      messageId: "message-path-switch",
      answer: {
        markdown: "I can help you change your active path.",
        confidence: "partial",
      },
      citations: [],
      actions: [
        {
          type: "request_path_switch",
          label: "Change path",
          actionId: "act-path-switch",
          status: "awaiting_confirmation",
        },
      ],
      warning: null,
    });
    agentApiMock.continueAction.mockResolvedValueOnce({
      conversationId: "conversation-1",
      messageId: "message-path-switch-committed",
      answer: {
        markdown: "I switched your active path and recalculated the learning plan.",
        confidence: "partial",
      },
      citations: [],
      actions: [],
      warning: null,
    });
    render(<AgentPage />);

    const promptButtons = await screen.findAllByRole("button", { name: /where should i review cnns/i });
    fireEvent.click(promptButtons[0]);

    expect(await screen.findByRole("combobox", { name: /target learning path/i })).toBeInTheDocument();
    const pathSelect = screen.getByRole("combobox", { name: /target learning path/i });
    expect(pathSelect).toHaveValue("computer_vision");
    expect(screen.getByRole("button", { name: "Repath" })).toBeDisabled();

    fireEvent.change(pathSelect, {
      target: { value: "nlp" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Repath" }));

    expect(await screen.findByRole("dialog", { name: /confirm path change/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(useLearningPathStore.getState().profile?.pathKey).toBe("computer_vision");

    fireEvent.click(screen.getByRole("button", { name: "Repath" }));
    fireEvent.click(await screen.findByRole("button", { name: "Change path" }));

    await waitFor(() => {
      expect(agentApiMock.continueAction).toHaveBeenCalledWith({
        conversationId: "conversation-1",
        actionId: "act-path-switch",
        decision: "approve",
        editPayload: { targetPathId: "nlp" },
        incomingMessageId: expect.any(String),
      });
    });
    expect(useLearningPathStore.getState().profile).toMatchObject({
      pathKey: "nlp",
      selectedCourseIds: ["CS230", "CS224n"],
      weeklyHours: 5,
      source: "manual",
    });
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
