import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BizInsight AI",
  description: "AI-powered customer feedback analytics platform.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📊</text></svg>" />
      </head>
      <body className="bg-white text-black dark:bg-zinc-900 dark:text-white transition-colors min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
