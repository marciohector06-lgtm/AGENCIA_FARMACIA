import type { Metadata, Viewport } from "next";
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
};

export const viewport: Viewport = {
  // Reforça (via <meta name="color-scheme">, além do CSS) que os
  // controles nativos do navegador — inclusive o popup de <select> —
  // devem renderizar no tema claro. Alguns navegadores/versões honram
  // esse hint de forma mais confiável do que só a propriedade CSS.
  colorScheme: "light",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex h-full min-h-screen text-slate-900">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
