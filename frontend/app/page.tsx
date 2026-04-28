import type { Metadata } from "next";

import LandingPage from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "Lộ trình học AI có định hướng",
  description:
    "Nền tảng học AI/ML/CV/NLP giúp bạn học có lộ trình, có hỗ trợ, và tiến bộ rõ ràng hơn.",
};

export default function RootPage() {
  return <LandingPage />;
}
