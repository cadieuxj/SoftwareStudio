'use client'

import { ClerkProvider } from '@clerk/nextjs'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect, type ReactNode } from 'react'
import { Toaster } from 'react-hot-toast'
import { useUIStore } from '@/store'

function ThemeSync() {
  const theme = useUIStore((s) => s.theme)
  useEffect(() => {
    const root = document.documentElement
    if (theme === 'light') {
      root.classList.remove('dark')
      root.classList.add('light')
    } else {
      root.classList.remove('light')
      root.classList.add('dark')
    }
  }, [theme])
  return null
}

interface ProvidersProps {
  children: ReactNode
}

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5000,
            refetchOnWindowFocus: false,
            retry: (failureCount, error) => {
              // Don't retry on 4xx errors
              if (error instanceof Error && 'status' in error) {
                const status = (error as { status: number }).status
                if (status >= 400 && status < 500) {
                  return false
                }
              }
              return failureCount < 3
            },
          },
          mutations: {
            retry: false,
          },
        },
      })
  )

  return (
    <ClerkProvider>
      <QueryClientProvider client={queryClient}>
        <ThemeSync />
        {children}
        <Toaster
          position="bottom-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: 'var(--background-secondary)',
              color: 'var(--foreground)',
              border: '1px solid var(--border-strong, rgba(99,102,241,0.2))',
              borderRadius: '10px',
              backdropFilter: 'blur(12px)',
              fontFamily: 'Inter, system-ui, sans-serif',
              fontSize: '13px',
            },
            success: {
              iconTheme: { primary: '#10b981', secondary: 'transparent' },
            },
            error: {
              iconTheme: { primary: '#ef4444', secondary: 'transparent' },
            },
          }}
        />
      </QueryClientProvider>
    </ClerkProvider>
  )
}
