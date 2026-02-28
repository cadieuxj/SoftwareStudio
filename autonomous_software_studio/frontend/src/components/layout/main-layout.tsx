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
      {/* Subtle ambient radial gradient for depth */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse 80% 40% at 50% -10%, rgba(99,102,241,0.06), transparent)',
        }}
      />

      <Sidebar />
      <Header />

      <main
        className={cn(
          'pt-14 min-h-screen transition-all duration-200 relative',
          sidebarOpen ? 'pl-[220px]' : 'pl-[60px]'
        )}
      >
        <div className="p-6">{children}</div>
      </main>

      <CreateSessionModal />
    </div>
  )
}
