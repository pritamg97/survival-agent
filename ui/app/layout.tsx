import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Survival Agent",
  description: "Earn or die. An autonomous agent's monthly survival dashboard.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg text-gray-200">{children}</body>
    </html>
  );
}
