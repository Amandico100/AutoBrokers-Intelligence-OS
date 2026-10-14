import './globals.css';
import type { Metadata, Viewport } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';

import { Toaster } from '@/components/ui/sonner';
import { ThemeProvider } from '@/components/theme-provider';

const geistSans = Geist({
  subsets: ['latin'],
  variable: '--font-geist-sans',
  display: 'swap',
});

const geistMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-geist-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'AutoBrokers Intelligence OS',
  description: 'AutoBrokers.ai operational intelligence platform',
  icons: {
    icon: '/autobrokers-mark.svg',
  },
};

/**
 * SPEC-132-A (B9) — o viewport do app. `interactive-widget=resizes-content`: o teclado do celular REDIMENSIONA o
 * conteúdo (o casco em `100dvh` encolhe e a caixa sobe junto), em vez de cobrir a tela e deixar a página rolar por
 * baixo. `viewport-fit=cover` libera o `env(safe-area-inset-bottom)` do iPhone. Referência: MDN, meta viewport.
 */
export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  interactiveWidget: 'resizes-content',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable}`}
    >
      <body className="font-sans antialiased">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem={false}
          disableTransitionOnChange
        >
          {children}
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
