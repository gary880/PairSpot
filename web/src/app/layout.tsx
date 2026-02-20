import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PairSpot",
  description: "PairSpot — couples app dev testing interface",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <main className="mx-auto max-w-md px-4 py-12">{children}</main>
      </body>
    </html>
  );
}
