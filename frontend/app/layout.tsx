// app/layout.tsx
// Root layout — provides ThemeProvider and font

import type { Metadata } from "next";
import Providers from "@/components/Providers";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "AI Learning Platform",
    template: "%s | AI Learning Platform",
  },
  description: "Adaptive AI-powered learning tailored to you.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <body>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
