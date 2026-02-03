'use client'

import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { useUIStore } from '@/store'
import { Sidebar } from './sidebar'
import { Header } from './header'
import { CreateSessionModal } from '@/components/sessions/create-session-modal'

interface MainLayoutProps {
  children: ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
  const { sidebarOpen } = useUIStore()

  return (
    <div className="min-h-screen bg-background">
      {/* Animated Grid Background */}
      <div className="fixed inset-0 cyber-grid opacity-30 pointer-events-none" />

      {/* Gradient Overlay */}
      <div className="fixed inset-0 bg-gradient-to-br from-neon-cyan/5 via-transparent to-neon-magenta/5 pointer-events-none" />

      {/* Sidebar */}
      <Sidebar />

      {/* Header */}
      <Header />

      {/* Main Content */}
      <main
        className={cn(
          'pt-16 min-h-screen transition-all duration-300 relative',
          sidebarOpen ? 'pl-[280px]' : 'pl-[80px]'
        )}
      >
        <div className="p-6">
          {children}
        </div>
      </main>

      {/* Global Modals */}
      <CreateSessionModal />
    </div>
  )
}
