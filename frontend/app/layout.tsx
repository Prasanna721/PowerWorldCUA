import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PowerWorld CUA",
  description: "Computer User Agent for PowerWorld Installation",
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
