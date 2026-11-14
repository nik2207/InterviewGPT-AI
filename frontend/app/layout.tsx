import type { Metadata } from "next";

import "./globals.css";
import { AuthProvider } from "@/providers/auth-provider";
import GoogleProvider from "@/providers/google-provider";

export const metadata: Metadata = {
  title: "InterviewGPT AI",
  description: "AI-powered interview preparation dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <GoogleProvider>
          <AuthProvider>{children}</AuthProvider>
        </GoogleProvider>
      </body>
    </html>
  );
}
