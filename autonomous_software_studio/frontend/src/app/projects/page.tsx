'use client'

import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  FolderKanban,
  ChevronDown,
  ChevronRight,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  CalendarDays,
} from 'lucide-react'
import { projectsApi, queryKeys } from '@/lib/api'
import { cn, formatDateTime, getStatusLabel } from '@/lib/utils'
import { Card, CardHeader, CardTitle, CardContent, Badge } from '@/components/ui'
import type { Session, SessionStatus } from '@/types'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function statusColor(status: SessionStatus): string {
  const map: Record<SessionStatus, string> = {
    pending: 'bg-amber-500/80',
    running: 'bg-indigo-500/90',
    awaiting_approval: 'bg-violet-500/80',
    completed: 'bg-emerald-500/80',
    failed: 'bg-red-500/80',
    expired: 'bg-zinc-500/80',
  }
  return map[status] ?? 'bg-zinc-500/80'
}

function statusIcon(status: SessionStatus) {
  if (status === 'running') return Activity
  if (status === 'completed') return CheckCircle2
  if (status === 'failed') return XCircle
  if (status === 'awaiting_approval') return AlertCircle
  return Clock
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface Project {
  name: string
  sessions: Session[]
  earliest: Date
  latest: Date
  completed: number
  running: number
  failed: number
}

// ─── Gantt bar ────────────────────────────────────────────────────────────────

function GanttBar({
  session,
  rangeStart,
  rangeEnd,
}: {
  session: Session
  rangeStart: number
  rangeEnd: number
}) {
  const start = new Date(session.created_at).getTime()
  const end = new Date(session.updated_at).getTime()
  const now = Date.now()
  const effectiveEnd = session.status === 'running' || session.status === 'pending' ? now : end

  const total = rangeEnd - rangeStart
  const left = Math.max(0, ((start - rangeStart) / total) * 100)
  const width = Math.max(0.5, ((effectiveEnd - start) / total) * 100)
  const clampedWidth = Math.min(width, 100 - left)

  const Icon = statusIcon(session.status)

  return (
    <div
      className="absolute top-1/2 -translate-y-1/2 h-6 rounded flex items-center gap-1 px-2 text-white text-[11px] font-medium overflow-hidden cursor-default group"
      style={{
        left: `${left}%`,
        width: `${clampedWidth}%`,
      }}
      title={`${session.project_name ?? 'Unnamed'} · ${getStatusLabel(session.status)}\n${formatDateTime(session.created_at)} → ${formatDateTime(session.updated_at)}`}
    >
      <div className={cn('absolute inset-0 rounded', statusColor(session.status))} />
      {session.status === 'running' && (
        <div className={cn('absolute inset-0 rounded animate-pulse opacity-40', statusColor(session.status))} />
      )}
      <Icon className="relative h-3 w-3 flex-shrink-0" />
      <span className="relative truncate leading-none">
        {session.project_name ?? session.mission?.slice(0, 30)}
      </span>
    </div>
  )
}

// ─── Timeline ticks ───────────────────────────────────────────────────────────

function TimelineTicks({ start, end, ticks }: { start: number; end: number; ticks: number }) {
  const total = end - start
  const step = total / ticks

  return (
    <div className="relative h-8 border-b border-white/[0.06] flex-shrink-0">
      {Array.from({ length: ticks + 1 }).map((_, i) => {
        const ts = start + i * step
        const d = new Date(ts)
        const label =
          total > 7 * 24 * 3600_000
            ? d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
            : total > 24 * 3600_000
            ? d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: 'numeric' })
            : d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })

        return (
          <div
            key={i}
            className="absolute top-0 bottom-0 flex flex-col justify-end"
            style={{ left: `${(i / ticks) * 100}%` }}
          >
            <div className="h-full w-px bg-white/[0.06]" />
            <span className="absolute bottom-1 left-1 text-[10px] text-foreground-subtle whitespace-nowrap">
              {label}
            </span>
          </div>
        )
      })}
    </div>
  )
}

// ─── Project row ──────────────────────────────────────────────────────────────

function ProjectRow({
  project,
  rangeStart,
  rangeEnd,
}: {
  project: Project
  rangeStart: number
  rangeEnd: number
}) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div>
      {/* Project header */}
      <div
        className="flex items-center gap-3 px-4 py-2.5 bg-background-secondary/60 border-b border-white/[0.04] cursor-pointer hover:bg-background-secondary/80 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-foreground-subtle" />
        ) : (
          <ChevronRight className="h-4 w-4 text-foreground-subtle" />
        )}
        <FolderKanban className="h-4 w-4 text-indigo-400" />
        <span className="text-sm font-medium text-foreground">{project.name}</span>
        <div className="flex items-center gap-1.5 ml-1">
          {project.running > 0 && (
            <Badge variant="running" className="text-[10px]">{project.running} running</Badge>
          )}
          {project.completed > 0 && (
            <Badge variant="completed" className="text-[10px]">{project.completed} done</Badge>
          )}
          {project.failed > 0 && (
            <Badge variant="failed" className="text-[10px]">{project.failed} failed</Badge>
          )}
        </div>
        <span className="ml-auto text-xs text-foreground-subtle">
          {project.sessions.length} session{project.sessions.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Gantt rows */}
      {expanded && (
        <div>
          {project.sessions.map((session) => (
            <div
              key={session.session_id}
              className="flex border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors"
            >
              {/* Label column */}
              <div className="w-56 flex-shrink-0 flex items-center gap-2 px-4 py-2 border-r border-white/[0.04]">
                <div className={cn('h-2 w-2 rounded-full', statusColor(session.status))} />
                <span
                  className="text-xs text-foreground-muted truncate"
                  title={session.mission}
                >
                  {session.mission?.slice(0, 32) ?? 'Unnamed session'}
                </span>
              </div>

              {/* Bar area */}
              <div className="flex-1 relative h-10">
                <GanttBar
                  session={session}
                  rangeStart={rangeStart}
                  rangeEnd={rangeEnd}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const ZOOM_LEVELS = [
  { label: '1d', ms: 24 * 3600_000 },
  { label: '7d', ms: 7 * 24 * 3600_000 },
  { label: '30d', ms: 30 * 24 * 3600_000 },
  { label: 'All', ms: 0 },
]

export default function ProjectsPage() {
  const [zoomIdx, setZoomIdx] = useState(2) // default 30d
  const { data: sessions, isLoading } = useQuery({
    queryKey: queryKeys.projects,
    queryFn: projectsApi.listSessions,
    staleTime: 30_000,
  })

  // Group by project name
  const projects = useMemo<Project[]>(() => {
    if (!sessions) return []
    const map = new Map<string, Session[]>()
    for (const s of sessions) {
      const key = s.project_name || 'Unnamed'
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(s)
    }
    return Array.from(map.entries())
      .map(([name, list]) => {
        const dates = list.flatMap((s) => [
          new Date(s.created_at).getTime(),
          new Date(s.updated_at).getTime(),
        ])
        return {
          name,
          sessions: list.sort(
            (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          ),
          earliest: new Date(Math.min(...dates)),
          latest: new Date(Math.max(...dates)),
          completed: list.filter((s) => s.status === 'completed').length,
          running: list.filter((s) => s.status === 'running').length,
          failed: list.filter((s) => s.status === 'failed').length,
        }
      })
      .sort((a, b) => b.latest.getTime() - a.latest.getTime())
  }, [sessions])

  // Calculate time range
  const { rangeStart, rangeEnd } = useMemo(() => {
    const now = Date.now()
    const zoomMs = ZOOM_LEVELS[zoomIdx].ms
    if (zoomMs === 0 || !sessions?.length) {
      // All time
      const allDates = sessions?.flatMap((s) => [
        new Date(s.created_at).getTime(),
        new Date(s.updated_at).getTime(),
      ]) ?? [now - 7 * 24 * 3600_000]
      const earliest = Math.min(...allDates)
      return { rangeStart: earliest - 3600_000, rangeEnd: now + 3600_000 }
    }
    return { rangeStart: now - zoomMs, rangeEnd: now + 3600_000 }
  }, [sessions, zoomIdx])

  const runningSessions = sessions?.filter((s) => s.status === 'running').length ?? 0
  const completedSessions = sessions?.filter((s) => s.status === 'completed').length ?? 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Projects</h1>
          <p className="text-sm text-foreground-muted mt-1">
            Session timeline by project
          </p>
        </div>

        {/* Zoom controls */}
        <div className="flex items-center gap-1 bg-background-secondary rounded-lg p-1 border border-white/[0.06]">
          {ZOOM_LEVELS.map((z, i) => (
            <button
              key={z.label}
              onClick={() => setZoomIdx(i)}
              className={cn(
                'px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
                i === zoomIdx
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-foreground-muted hover:text-foreground hover:bg-white/[0.05]'
              )}
            >
              {z.label}
            </button>
          ))}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-foreground-muted">Projects</p>
            <p className="text-2xl font-semibold text-foreground mt-1">
              {isLoading ? '—' : projects.length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-foreground-muted">Active sessions</p>
            <p className="text-2xl font-semibold text-indigo-400 mt-1">
              {isLoading ? '—' : runningSessions}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-foreground-muted">Completed</p>
            <p className="text-2xl font-semibold text-emerald-400 mt-1">
              {isLoading ? '—' : completedSessions}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Gantt chart */}
      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarDays className="h-4 w-4 text-indigo-400" />
            Timeline
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading && (
            <div className="p-8 text-center text-foreground-muted text-sm">
              Loading timeline…
            </div>
          )}

          {!isLoading && projects.length === 0 && (
            <div className="p-12 text-center">
              <FolderKanban className="h-10 w-10 text-foreground-subtle mx-auto mb-3" />
              <p className="text-foreground-muted text-sm">No sessions yet</p>
              <p className="text-xs text-foreground-subtle mt-1">
                Create sessions to see them on the timeline
              </p>
            </div>
          )}

          {!isLoading && projects.length > 0 && (
            <div>
              {/* Fixed header: label col + timeline ticks */}
              <div className="flex border-b border-white/[0.06]">
                <div className="w-56 flex-shrink-0 border-r border-white/[0.06] px-4 py-2">
                  <span className="text-[10px] font-medium text-foreground-subtle uppercase tracking-wider">
                    Session
                  </span>
                </div>
                <div className="flex-1">
                  <TimelineTicks start={rangeStart} end={rangeEnd} ticks={6} />
                </div>
              </div>

              {/* Project rows */}
              <div className="max-h-[600px] overflow-y-auto">
                {projects.map((p) => (
                  <ProjectRow
                    key={p.name}
                    project={p}
                    rangeStart={rangeStart}
                    rangeEnd={rangeEnd}
                  />
                ))}
              </div>

              {/* Legend */}
              <div className="flex items-center gap-4 px-4 py-3 border-t border-white/[0.06] flex-wrap">
                {(
                  [
                    ['pending', 'Pending'],
                    ['running', 'Running'],
                    ['awaiting_approval', 'Awaiting review'],
                    ['completed', 'Completed'],
                    ['failed', 'Failed'],
                  ] as [SessionStatus, string][]
                ).map(([status, label]) => (
                  <div key={status} className="flex items-center gap-1.5 text-xs text-foreground-muted">
                    <div className={cn('h-2.5 w-2.5 rounded-sm', statusColor(status))} />
                    {label}
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
