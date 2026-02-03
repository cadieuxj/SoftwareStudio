import type { Metadata, Viewport } from 'next'
import { Providers } from '@/providers'
import { MainLayout } from '@/components/layout'
import './globals.css'

export const metadata: Metadata = {
  title: 'AutoStudio | Autonomous Software Factory',
  description: 'AI-powered software development with multi-agent orchestration. Build production-ready applications with autonomous agents.',
  keywords: ['AI', 'software development', 'autonomous agents', 'code generation', 'multi-agent'],
  authors: [{ name: 'AutoStudio Team' }],
  openGraph: {
    title: 'AutoStudio | Autonomous Software Factory',
    description: 'AI-powered software development with multi-agent orchestration',
    type: 'website',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#0a0a0f',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="font-body antialiased">
        <Providers>
          <MainLayout>{children}</MainLayout>
        </Providers>
      </body>
    </html>
  )
}
