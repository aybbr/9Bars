import type { Metadata } from "next";
import { Fraunces, Geist, JetBrains_Mono } from "next/font/google";
import { AppShell } from "@/components/AppShell";
import { ChatProvider } from "@/lib/chat-context";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  axes: ["opsz", "SOFT", "WONK"],
});
const geist = Geist({ subsets: ["latin"], variable: "--font-geist" });
const jetbrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains" });

export const metadata: Metadata = {
  title: "9Bars",
  description: "Nine bars of pressure. None on you.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${fraunces.variable} ${geist.variable} ${jetbrains.variable}`}>
      <body className="grain min-h-dvh antialiased">
        <ChatProvider>
          <AppShell>{children}</AppShell>
        </ChatProvider>
      </body>
    </html>
  );
}
