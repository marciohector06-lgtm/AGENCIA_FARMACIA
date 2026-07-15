import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/AppShell";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Farmácia MAS",
  description: "Painel de gestão e atendimento com agentes de IA",
  // Reforça (via <meta name="color-scheme">, além do CSS) que os
  // controles nativos do navegador — inclusive o popup de <select> —
  // devem renderizar no tema escuro. Alguns navegadores/versões honram
  // esse hint de forma mais confiável do que só a propriedade CSS.
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex h-full min-h-screen text-slate-100">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
