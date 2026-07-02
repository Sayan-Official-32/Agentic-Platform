import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Multi Agent Starter UI",
  description: "Beginner-friendly multi-agent chat UI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}



