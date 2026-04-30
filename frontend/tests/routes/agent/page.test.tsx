import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AgentPage from "@/app/agent/page";

const agentApiMock = vi.hoisted(() => ({
  listConversations: vi.fn(),
  createConversation: vi.fn(),
  messages: vi.fn(),
  memory: vi.fn(),
  chat: vi.fn(),
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

  it("sends a chat message and renders answer citations", async () => {
    render(<AgentPage />);

    const promptButtons = await screen.findAllByRole("button", { name: /where should i review cnns/i });
    fireEvent.click(promptButtons[0]);

    await waitFor(() => {
      expect(agentApiMock.chat).toHaveBeenCalledWith({
        message: "Where should I review CNNs?",
        conversationId: null,
        traceMode: "summary",
      });
    });

    expect(await screen.findByText("Receptive fields are covered in CS231n.")).toBeInTheDocument();
    expect(screen.getByText("Kernels, stride, pooling, and receptive fields")).toBeInTheDocument();
  });
});
