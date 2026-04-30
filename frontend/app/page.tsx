import type { Metadata } from "next";

import LandingPage from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "A Clearer Path to Learning AI",
  description:
    "A structured learning experience that helps beginners and self-learners study AI with more clarity and less scattered effort.",
};

export default function RootPage() {
  return <LandingPage />;
}
