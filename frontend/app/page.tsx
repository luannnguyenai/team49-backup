import type { Metadata } from "next";

import LandingPage from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "Guided AI Learning Path",
  description:
    "An AI/ML/CV/NLP learning platform that gives you structure, support, and clearer progress.",
};

export default function RootPage() {
  return <LandingPage />;
}
