'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import Link from 'next/link'
import {
  LayoutGrid,
  List,
  Plus,
  Activity,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Filter,
  Search,
} from 'lucide-react'
import { sessionsApi, queryKeys } from '@/lib/api'
import {
  cn,
  formatRelativeTime,
  getStatusLabel,
  getPhaseLabel,
  truncate,
} from '@/lib/utils'
import { useUIStore, useCreateSessionModal } from '@/store'
import type { Session, SessionStatus } from '@/types'
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  Button,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Progress,
} from '@/components/ui'

const statusColumns: { status: SessionStatus; label: string; color: string; icon: typeof Activity }[] = [
  { status: 'pending', label: 'Pending', color: 'neon-orange', icon: Clock },
  { status: 'running', label: 'Running', color: 'neon-cyan', icon: Activity },
  { status: 'awaiting_approval', label: 'Awaiting Review', color: 'neon-magenta', icon: AlertCircle },
  { status: 'completed', label: 'Completed', color: 'neon-green', icon: CheckCircle2 },
  { status: 'failed', label: 'Failed', color: 'red-400', icon: XCircle },
]

function SessionCard({ session }: { session: Session }) {
  const Icon = statusColumns.find((c) => c.status === session.status)?.icon || Clock

  return (
    <Link href={`/sessions/${session.session_id}`}>
      <motion.div
        layout
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        className={cn(
          'p-4 rounded-lg bg-background-secondary/80 border border-border',
          'hover:border-neon-cyan/30 hover:shadow-glow cursor-pointer',
          'transition-all duration-300 group'
        )}
      >
        <div className="flex items-start justify-between gap-2 mb-3">
          <h4 className="font-display font-semibold text-foreground group-hover:text-neon-cyan transition-colors truncate">
            {session.project_name}
          </h4>
          <Icon className={cn(
            'h-4 w-4 shrink-0',
            session.status === 'running' && 'text-neon-cyan animate-pulse',
            session.status === 'awaiting_approval' && 'text-neon-magenta',
            session.status === 'completed' && 'text-neon-green',
            session.status === 'failed' && 'text-red-400',
            session.status === 'pending' && 'text-neon-orange'
          )} />
        </div>

        <p className="text-sm text-foreground-muted mb-3 line-clamp-2">
          {truncate(session.mission, 100)}
        </p>

        <div className="flex items-center justify-between">
          <Badge variant="secondary" size="sm">
            {getPhaseLabel(session.phase)}
          </Badge>
          <span className="text-xs text-foreground-subtle">
            {formatRelativeTime(session.updated_at)}
          </span>
        </div>

        {session.status === 'running' && (
          <div className="mt-3">
            <Progress value={50} className="h-1" />
          </div>
        )}

        {session.iteration_count > 0 && (
          <div className="mt-2 text-xs text-foreground-subtle">
            Iteration {session.iteration_count}
          </div>
        )}
      </motion.div>
    </Link>
  )
}

function KanbanColumn({
  status,
  label,
  color,
  icon: Icon,
  sessions,
}: {
  status: SessionStatus
  label: string
  color: string
  icon: typeof Activity
  sessions: Session[]
}) {
  const count = sessions.length

  return (
    <div className="flex flex-col min-w-[300px] max-w-[300px]">
      <div className={cn(
        'flex items-center gap-3 p-4 rounded-t-lg border-b-2',
        `border-${color}`,
        'bg-background-secondary/50'
      )}>
        <Icon className={cn('h-5 w-5', `text-${color}`)} />
        <h3 className="font-display font-semibold text-foreground">{label}</h3>
        <Badge variant="secondary" size="sm" className="ml-auto">
          {count}
        </Badge>
      </div>

      <div className="flex-1 p-3 space-y-3 bg-background-secondary/30 rounded-b-lg min-h-[400px] max-h-[calc(100vh-300px)] overflow-y-auto">
        {sessions.map((session) => (
          <SessionCard key={session.session_id} session={session} />
        ))}
        {sessions.length === 0 && (
          <div className="py-8 text-center text-foreground-subtle text-sm">
            No sessions
          </div>
        )}
      </div>
    </div>
  )
}

function ListView({ sessions }: { sessions: Session[] }) {
  return (
    <div className="space-y-3">
      {sessions.map((session) => (
        <Link
          key={session.session_id}
          href={`/sessions/${session.session_id}`}
          className={cn(
            'flex items-center gap-4 p-4 rounded-lg',
            'bg-background-secondary/50 border border-border',
            'hover:border-neon-cyan/30 hover:shadow-glow',
            'transition-all duration-300 group'
          )}
        >
          <div className={cn(
            'h-12 w-12 rounded-lg flex items-center justify-center shrink-0',
            session.status === 'running' && 'bg-neon-cyan/10 border border-neon-cyan/30',
            session.status === 'awaiting_approval' && 'bg-neon-magenta/10 border border-neon-magenta/30',
            session.status === 'completed' && 'bg-neon-green/10 border border-neon-green/30',
            session.status === 'failed' && 'bg-red-500/10 border border-red-500/30',
            session.status === 'pending' && 'bg-neon-orange/10 border border-neon-orange/30'
          )}>
            {session.status === 'running' && <Activity className="h-6 w-6 text-neon-cyan animate-pulse" />}
            {session.status === 'awaiting_approval' && <AlertCircle className="h-6 w-6 text-neon-magenta" />}
            {session.status === 'completed' && <CheckCircle2 className="h-6 w-6 text-neon-green" />}
            {session.status === 'failed' && <XCircle className="h-6 w-6 text-red-400" />}
            {session.status === 'pending' && <Clock className="h-6 w-6 text-neon-orange" />}
          </div>

          <div className="flex-1 min-w-0">
            <h4 className="font-display font-semibold text-foreground group-hover:text-neon-cyan transition-colors">
              {session.project_name}
            </h4>
            <p className="text-sm text-foreground-muted truncate">
              {session.mission}
            </p>
          </div>

          <div className="flex items-center gap-4 shrink-0">
            <Badge variant="secondary">
              {getPhaseLabel(session.phase)}
            </Badge>
            <Badge
              variant={
                session.status === 'running' ? 'running' :
                session.status === 'awaiting_approval' ? 'awaiting' :
                session.status === 'completed' ? 'completed' :
                session.status === 'failed' ? 'failed' :
                'pending'
              }
            >
              {getStatusLabel(session.status)}
            </Badge>
            <span className="text-sm text-foreground-subtle min-w-[100px] text-right">
              {formatRelativeTime(session.updated_at)}
            </span>
          </div>
        </Link>
      ))}
      {sessions.length === 0 && (
        <div className="py-16 text-center">
          <p className="text-foreground-muted">No sessions found</p>
        </div>
      )}
    </div>
  )
}

export default function SessionsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<SessionStatus | 'all'>('all')
  const { kanbanViewEnabled, setKanbanViewEnabled } = useUIStore()
  const openCreateModal = useCreateSessionModal((s) => s.open)

  const { data: sessions = [], isLoading } = useQuery({
    queryKey: queryKeys.sessions,
    queryFn: () => sessionsApi.list(),
    refetchInterval: 10000,
  })

  // Filter sessions
  const filteredSessions = sessions.filter((session) => {
    const matchesSearch =
      session.project_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.mission.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'all' || session.status === statusFilter
    return matchesSearch && matchesStatus
  })

  // Group sessions by status for kanban
  const sessionsByStatus = statusColumns.reduce((acc, col) => {
    acc[col.status] = filteredSessions.filter((s) => s.status === col.status)
    return acc
  }, {} as Record<SessionStatus, Session[]>)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-foreground">
            Sessions
          </h1>
          <p className="text-foreground-muted mt-1">
            Manage and monitor your development sessions
          </p>
        </div>
        <Button onClick={() => openCreateModal()} className="gap-2">
          <Plus className="h-4 w-4" />
          New Session
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex-1 min-w-[200px] max-w-md">
              <Input
                placeholder="Search sessions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                icon={<Search className="h-4 w-4" />}
              />
            </div>

            <Select
              value={statusFilter}
              onValueChange={(v) => setStatusFilter(v as SessionStatus | 'all')}
            >
              <SelectTrigger className="w-[180px]">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                {statusColumns.map((col) => (
                  <SelectItem key={col.status} value={col.status}>
                    {col.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="flex items-center gap-2 ml-auto">
              <Button
                variant={kanbanViewEnabled ? 'default' : 'outline'}
                size="icon"
                onClick={() => setKanbanViewEnabled(true)}
              >
                <LayoutGrid className="h-4 w-4" />
              </Button>
              <Button
                variant={!kanbanViewEnabled ? 'default' : 'outline'}
                size="icon"
                onClick={() => setKanbanViewEnabled(false)}
              >
                <List className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Sessions View */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="spinner h-8 w-8" />
        </div>
      ) : kanbanViewEnabled ? (
        <div className="overflow-x-auto pb-4">
          <div className="flex gap-4 min-w-min">
            {statusColumns.map((col) => (
              <KanbanColumn
                key={col.status}
                status={col.status}
                label={col.label}
                color={col.color}
                icon={col.icon}
                sessions={sessionsByStatus[col.status] || []}
              />
            ))}
          </div>
        </div>
      ) : (
        <ListView sessions={filteredSessions} />
      )}
    </div>
  )
}
