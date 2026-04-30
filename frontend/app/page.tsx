import type { Metadata } from "next";

import LandingPage from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "Home",
  description:
    "A structured learning experience that helps beginners and self-learners study AI with more clarity and less scattered effort.",
};

export default function RootPage() {
  return <LandingPage />;
}
