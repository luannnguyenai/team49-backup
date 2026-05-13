import type { Metadata } from "next";

import LandingPage from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "AI Learning Hub - Your Personal Path to Mastery",
  description:
    "Adaptive, tailored learning modules created just for your goals. Start your structured AI learning journey today.",
};

export default function RootPage() {
  return <LandingPage />;
}
