'use client'

import { useState, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Activity,
  RefreshCw,
  Pause,
  Play,
  Search,
  Filter,
  Download,
  Trash2,
  Terminal,
} from 'lucide-react'
import { sessionsApi, queryKeys } from '@/lib/api'
import { cn, formatDateTime } from '@/lib/utils'
import { useUIStore } from '@/store'
import type { LogEntry, SessionStatus } from '@/types'
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
  Switch,
  ScrollArea,
} from '@/components/ui'

const logLevelColors = {
  debug: 'text-foreground-subtle',
  info: 'text-neon-cyan',
  warning: 'text-neon-orange',
  error: 'text-red-400',
}

export default function LogsPage() {
  const [selectedSession, setSelectedSession] = useState<string>('all')
  const [levelFilter, setLevelFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const { logsAutoRefresh, setLogsAutoRefresh, logsRefreshInterval } = useUIStore()
  const scrollRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  const { data: sessions = [] } = useQuery({
    queryKey: queryKeys.sessions,
    queryFn: () => sessionsApi.list(),
  })

  const runningSessions = sessions.filter((s) => s.status === 'running')

  const { data: logs = [], isLoading } = useQuery({
    queryKey: selectedSession !== 'all'
      ? queryKeys.sessionLogs(selectedSession)
      : [...queryKeys.sessions, 'logs'],
    queryFn: async () => {
      if (selectedSession !== 'all') {
        return sessionsApi.getLogs(selectedSession, 100)
      }
      // Aggregate logs from all running sessions
      const allLogs: LogEntry[] = []
      for (const session of runningSessions.slice(0, 5)) {
        try {
          const sessionLogs = await sessionsApi.getLogs(session.session_id, 20)
          allLogs.push(...sessionLogs.map(log => ({ ...log, session_id: session.session_id })))
        } catch {
          // Skip failed sessions
        }
      }
      return allLogs.sort((a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      )
    },
    refetchInterval: logsAutoRefresh ? logsRefreshInterval : false,
  })

  // Filter logs
  const filteredLogs = logs.filter((log) => {
    const matchesLevel = levelFilter === 'all' || log.level === levelFilter
    const matchesSearch =
      searchQuery === '' ||
      log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (log.agent && log.agent.toLowerCase().includes(searchQuery.toLowerCase()))
    return matchesLevel && matchesSearch
  })

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (scrollRef.current && logsAutoRefresh) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs, logsAutoRefresh])

  const handleRefresh = () => {
    queryClient.invalidateQueries({
      queryKey: selectedSession !== 'all'
        ? queryKeys.sessionLogs(selectedSession)
        : [...queryKeys.sessions, 'logs'],
    })
  }

  const handleExport = () => {
    const content = filteredLogs
      .map((log) =>
        `[${formatDateTime(log.timestamp)}] [${log.level.toUpperCase()}]${log.agent ? ` [${log.agent}]` : ''} ${log.message}`
      )
      .join('\n')

    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `logs-${new Date().toISOString().slice(0, 10)}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-foreground">
            Live Logs
          </h1>
          <p className="text-foreground-muted mt-1">
            Real-time execution logs from your sessions
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-background-secondary border border-border">
            <span className="text-sm text-foreground-muted">Auto-refresh</span>
            <Switch
              checked={logsAutoRefresh}
              onCheckedChange={setLogsAutoRefresh}
            />
          </div>
          {logsAutoRefresh && (
            <Badge variant="running" className="gap-2">
              <Activity className="h-3 w-3 animate-pulse" />
              Live
            </Badge>
          )}
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex-1 min-w-[200px] max-w-md">
              <Input
                placeholder="Search logs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                icon={<Search className="h-4 w-4" />}
              />
            </div>

            <Select
              value={selectedSession}
              onValueChange={setSelectedSession}
            >
              <SelectTrigger className="w-[250px]">
                <SelectValue placeholder="Select session" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Running Sessions</SelectItem>
                {sessions.map((session) => (
                  <SelectItem key={session.session_id} value={session.session_id}>
                    {session.project_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={levelFilter} onValueChange={setLevelFilter}>
              <SelectTrigger className="w-[150px]">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Level" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Levels</SelectItem>
                <SelectItem value="debug">Debug</SelectItem>
                <SelectItem value="info">Info</SelectItem>
                <SelectItem value="warning">Warning</SelectItem>
                <SelectItem value="error">Error</SelectItem>
              </SelectContent>
            </Select>

            <div className="flex items-center gap-2 ml-auto">
              <Button variant="outline" size="sm" onClick={handleRefresh}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Button variant="outline" size="sm" onClick={handleExport}>
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Log Viewer */}
      <Card className="relative">
        <CardHeader className="flex flex-row items-center justify-between border-b border-border">
          <CardTitle className="flex items-center gap-2">
            <Terminal className="h-5 w-5 text-neon-cyan" />
            Log Output
          </CardTitle>
          <Badge variant="secondary">
            {filteredLogs.length} entries
          </Badge>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="spinner h-8 w-8" />
            </div>
          ) : (
            <ScrollArea
              className="h-[600px] bg-background-secondary/50"
              ref={scrollRef}
            >
              <div className="p-4 font-mono text-sm space-y-0.5">
                {filteredLogs.length > 0 ? (
                  filteredLogs.map((log, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.15 }}
                      className="flex gap-3 py-1 px-2 hover:bg-background-tertiary/50 rounded"
                    >
                      <span className="text-foreground-subtle shrink-0 w-[140px]">
                        {formatDateTime(log.timestamp).slice(11)}
                      </span>
                      <span
                        className={cn(
                          'uppercase text-xs font-semibold shrink-0 w-16',
                          logLevelColors[log.level]
                        )}
                      >
                        [{log.level}]
                      </span>
                      {log.agent && (
                        <span className="text-neon-magenta shrink-0 w-20">
                          [{log.agent}]
                        </span>
                      )}
                      {log.session_id && selectedSession === 'all' && (
                        <span className="text-neon-green/50 shrink-0 w-32 truncate">
                          [{log.session_id.slice(0, 8)}]
                        </span>
                      )}
                      <span className={cn(
                        'text-foreground flex-1',
                        log.level === 'error' && 'text-red-400'
                      )}>
                        {log.message}
                      </span>
                    </motion.div>
                  ))
                ) : (
                  <div className="py-16 text-center text-foreground-muted">
                    No logs to display
                  </div>
                )}
              </div>
            </ScrollArea>
          )}
        </CardContent>

        {/* Floating Controls */}
        <div className="absolute bottom-4 right-4 flex gap-2">
          <Button
            variant="secondary"
            size="icon-sm"
            onClick={() => setLogsAutoRefresh(!logsAutoRefresh)}
          >
            {logsAutoRefresh ? (
              <Pause className="h-4 w-4" />
            ) : (
              <Play className="h-4 w-4" />
            )}
          </Button>
        </div>
      </Card>

      {/* Running Sessions */}
      {runningSessions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-neon-cyan animate-pulse" />
              Active Sessions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {runningSessions.map((session) => (
                <div
                  key={session.session_id}
                  className={cn(
                    'p-4 rounded-lg border cursor-pointer transition-all duration-300',
                    selectedSession === session.session_id
                      ? 'border-neon-cyan bg-neon-cyan/10'
                      : 'border-border bg-background-secondary hover:border-neon-cyan/50'
                  )}
                  onClick={() => setSelectedSession(session.session_id)}
                >
                  <div className="flex items-center gap-3">
                    <Activity className="h-5 w-5 text-neon-cyan animate-pulse" />
                    <div>
                      <p className="font-display font-semibold text-foreground">
                        {session.project_name}
                      </p>
                      <p className="text-xs text-foreground-muted">
                        Phase: {session.phase}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
