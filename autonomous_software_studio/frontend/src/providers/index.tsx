'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import { Toaster } from 'react-hot-toast'

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
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="bottom-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: 'rgba(20, 20, 30, 0.95)',
            color: '#e8e8f0',
            border: '1px solid rgba(100, 100, 150, 0.3)',
            borderRadius: '12px',
            backdropFilter: 'blur(12px)',
            fontFamily: 'Rajdhani, sans-serif',
          },
          success: {
            iconTheme: {
              primary: '#00ff88',
              secondary: '#0a0a0f',
            },
            style: {
              borderColor: 'rgba(0, 255, 136, 0.5)',
            },
          },
          error: {
            iconTheme: {
              primary: '#ff4444',
              secondary: '#0a0a0f',
            },
            style: {
              borderColor: 'rgba(255, 68, 68, 0.5)',
            },
          },
        }}
      />
    </QueryClientProvider>
  )
}
