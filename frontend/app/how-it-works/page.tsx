import type { Metadata } from "next";
import LandingPage from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "How It Works - AI Learning Hub",
  description: "Learn how our structured AI learning paths can help you master AI concepts effectively.",
};

export default function HowItWorksPage() {
  return <LandingPage />;
}
