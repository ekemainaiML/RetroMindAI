import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import AuthGuard from "@/components/AuthGuard";
import AppShell from "@/components/AppShell";
import ApiKeyInit from "@/components/ApiKeyInit";
import BrandingInit from "@/components/BrandingInit";
import ErrorBoundary from "@/components/ErrorBoundary";
import { UserProvider } from "@/contexts/UserContext";
import { ThemeProvider } from "@/contexts/ThemeContext";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RetroMind AI — EV Retrofit Intelligence",
  description: "Self-learning EV retrofit intelligence network for automotive workshops",
  manifest: "/manifest.json",
};

const themeScript = `
  (function() {
    try {
      var theme = localStorage.getItem('retromind_theme');
      if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
      }
    } catch(e) {}
  })();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  navigator.serviceWorker.register('/sw.js');
                });
              }
            `,
          }}
        />
      </head>
      <body className="min-h-full flex flex-col">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-text-primary focus:px-4 focus:py-2 focus:text-sm focus:text-[rgb(var(--surface))]"
        >
          Skip to main content
        </a>
        <ThemeProvider>
          <UserProvider>
            <ApiKeyInit />
            <BrandingInit />
            <ErrorBoundary>
              <AuthGuard>
                <AppShell>{children}</AppShell>
              </AuthGuard>
            </ErrorBoundary>
          </UserProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
