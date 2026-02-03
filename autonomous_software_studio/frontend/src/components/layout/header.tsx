'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Bell,
  Search,
  Plus,
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
} from 'lucide-react'
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
  Badge,
} from '@/components/ui'

export function Header() {
  const [searchQuery, setSearchQuery] = useState('')
  const { sidebarOpen } = useUIStore()
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
        'fixed top-0 right-0 z-30 h-16',
        'bg-background/80 backdrop-blur-xl',
        'border-b border-border',
        'flex items-center justify-between px-6',
        'transition-all duration-300',
        sidebarOpen ? 'left-[280px]' : 'left-[80px]'
      )}
    >
      {/* Search */}
      <div className="flex items-center gap-4 flex-1 max-w-md">
        <div className="relative flex-1">
          <Input
            placeholder="Search sessions, projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            icon={<Search className="h-4 w-4" />}
            className="h-10"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4">
        {/* Quick Stats */}
        <div className="hidden lg:flex items-center gap-3">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-background-secondary border border-border"
          >
            <Activity className="h-4 w-4 text-neon-cyan" />
            <span className="text-sm font-mono text-neon-cyan">
              {metrics?.running_sessions || 0}
            </span>
            <span className="text-xs text-foreground-subtle">Running</span>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-background-secondary border border-border"
          >
            <Clock className="h-4 w-4 text-neon-magenta" />
            <span className="text-sm font-mono text-neon-magenta">
              {metrics?.awaiting_approval || 0}
            </span>
            <span className="text-xs text-foreground-subtle">Pending</span>
          </motion.div>
        </div>

        {/* System Status */}
        <div
          className={cn(
            'flex items-center gap-2 px-3 py-1.5 rounded-full border',
            isHealthy
              ? 'border-neon-green/50 bg-neon-green/10'
              : 'border-red-500/50 bg-red-500/10'
          )}
        >
          <div
            className={cn(
              'h-2 w-2 rounded-full',
              isHealthy ? 'bg-neon-green animate-pulse' : 'bg-red-500'
            )}
          />
          <span
            className={cn(
              'text-xs font-display uppercase tracking-wider',
              isHealthy ? 'text-neon-green' : 'text-red-400'
            )}
          >
            {isHealthy ? 'Online' : 'Offline'}
          </span>
        </div>

        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              {(metrics?.awaiting_approval || 0) > 0 && (
                <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-neon-magenta text-[10px] font-bold flex items-center justify-center text-background">
                  {metrics?.awaiting_approval}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel>Notifications</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {(metrics?.awaiting_approval || 0) > 0 && (
              <DropdownMenuItem className="flex items-start gap-3 py-3">
                <AlertCircle className="h-5 w-5 text-neon-magenta shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium">
                    {metrics?.awaiting_approval} sessions awaiting approval
                  </p>
                  <p className="text-xs text-foreground-muted mt-1">
                    Review and approve to continue
                  </p>
                </div>
              </DropdownMenuItem>
            )}
            {(metrics?.completed_sessions || 0) > 0 && (
              <DropdownMenuItem className="flex items-start gap-3 py-3">
                <CheckCircle2 className="h-5 w-5 text-neon-green shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium">
                    {metrics?.completed_sessions} sessions completed
                  </p>
                  <p className="text-xs text-foreground-muted mt-1">
                    All tasks finished successfully
                  </p>
                </div>
              </DropdownMenuItem>
            )}
            {(metrics?.failed_sessions || 0) > 0 && (
              <DropdownMenuItem className="flex items-start gap-3 py-3">
                <AlertCircle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium">
                    {metrics?.failed_sessions} sessions failed
                  </p>
                  <p className="text-xs text-foreground-muted mt-1">
                    Check logs for details
                  </p>
                </div>
              </DropdownMenuItem>
            )}
            {!metrics?.awaiting_approval && !metrics?.completed_sessions && !metrics?.failed_sessions && (
              <div className="py-6 text-center text-foreground-muted text-sm">
                No new notifications
              </div>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* New Session Button */}
        <Button onClick={() => openCreateModal()} className="gap-2">
          <Plus className="h-4 w-4" />
          <span className="hidden sm:inline">New Session</span>
        </Button>
      </div>
    </header>
  )
}
