'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Bell,
  Search,
  Plus,
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  Sun,
  Moon,
} from 'lucide-react'
import { UserButton } from '@clerk/nextjs'
import { cn } from '@/lib/utils'
import { metricsApi, queryKeys } from '@/lib/api'
import { useUIStore, useCreateSessionModal } from '@/store'
import {
  Button,
  Input,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui'

export function Header() {
  const [searchQuery, setSearchQuery] = useState('')
  const { sidebarOpen, theme, setTheme } = useUIStore()
  const openCreateModal = useCreateSessionModal((s) => s.open)

  const { data: health } = useQuery({
    queryKey: queryKeys.health,
    queryFn: metricsApi.getHealth,
    refetchInterval: 30000,
  })

  const { data: metrics } = useQuery({
    queryKey: queryKeys.metrics,
    queryFn: metricsApi.get,
    refetchInterval: 10000,
  })

  const isHealthy = health?.status === 'healthy'

  return (
    <header
      className={cn(
        'fixed top-0 right-0 z-30 h-14',
        'bg-background backdrop-blur-md',
        'border-b border-border',
        'flex items-center justify-between px-5 gap-4',
        'transition-all duration-200',
        sidebarOpen ? 'left-[220px]' : 'left-[60px]'
      )}
    >
      {/* Search */}
      <div className="flex-1 max-w-sm">
        <Input
          placeholder="Search sessions, projects…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          icon={<Search className="h-3.5 w-3.5" />}
          className="h-8 text-sm"
        />
      </div>

      {/* Right */}
      <div className="flex items-center gap-2">
        {/* Stat chips */}
        <div className="hidden lg:flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/[0.04] border border-white/[0.07]">
            <Activity className="h-3.5 w-3.5 text-indigo-400" />
            <span className="text-xs font-mono text-foreground">
              {metrics?.running_sessions ?? 0}
            </span>
            <span className="text-xs text-foreground-subtle">running</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/[0.04] border border-white/[0.07]">
            <Clock className="h-3.5 w-3.5 text-violet-400" />
            <span className="text-xs font-mono text-foreground">
              {metrics?.awaiting_approval ?? 0}
            </span>
            <span className="text-xs text-foreground-subtle">pending</span>
          </div>
        </div>

        {/* Health dot */}
        <div
          className={cn(
            'flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs',
            isHealthy
              ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-400'
              : 'border-red-500/20 bg-red-500/5 text-red-400'
          )}
        >
          <span
            className={cn(
              'h-1.5 w-1.5 rounded-full',
              isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
            )}
          />
          {isHealthy ? 'Online' : 'Offline'}
        </div>

        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" className="relative">
              <Bell className="h-4 w-4" />
              {(metrics?.awaiting_approval ?? 0) > 0 && (
                <span className="absolute -top-0.5 -right-0.5 h-3.5 w-3.5 rounded-full bg-violet-500 text-[9px] font-bold flex items-center justify-center text-white">
                  {metrics?.awaiting_approval}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-72">
            <DropdownMenuLabel>Notifications</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {(metrics?.awaiting_approval ?? 0) > 0 && (
              <DropdownMenuItem className="flex items-start gap-3 py-3">
                <AlertCircle className="h-4 w-4 text-violet-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium">
                    {metrics?.awaiting_approval} awaiting approval
                  </p>
                  <p className="text-xs text-foreground-muted mt-0.5">
                    Review and approve to continue
                  </p>
                </div>
              </DropdownMenuItem>
            )}
            {(metrics?.completed_sessions ?? 0) > 0 && (
              <DropdownMenuItem className="flex items-start gap-3 py-3">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium">
                    {metrics?.completed_sessions} sessions completed
                  </p>
                  <p className="text-xs text-foreground-muted mt-0.5">
                    All tasks finished successfully
                  </p>
                </div>
              </DropdownMenuItem>
            )}
            {(metrics?.failed_sessions ?? 0) > 0 && (
              <DropdownMenuItem className="flex items-start gap-3 py-3">
                <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium">
                    {metrics?.failed_sessions} sessions failed
                  </p>
                  <p className="text-xs text-foreground-muted mt-0.5">
                    Check logs for details
                  </p>
                </div>
              </DropdownMenuItem>
            )}
            {!metrics?.awaiting_approval && !metrics?.completed_sessions && !metrics?.failed_sessions && (
              <div className="py-5 text-center text-foreground-muted text-sm">
                No new notifications
              </div>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Theme toggle */}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          aria-label="Toggle theme"
        >
          {theme === 'dark'
            ? <Sun className="h-4 w-4" />
            : <Moon className="h-4 w-4" />
          }
        </Button>

        {/* New Session */}
        <Button size="sm" onClick={() => openCreateModal()} className="gap-1.5">
          <Plus className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">New Session</span>
        </Button>

        {/* User profile */}
        <UserButton
          afterSignOutUrl="/sign-in"
          appearance={{
            elements: {
              avatarBox: 'h-8 w-8 rounded-lg',
              userButtonTrigger: 'rounded-lg focus:ring-1 focus:ring-indigo-500/50',
            },
          }}
        />
      </div>
    </header>
  )
}
