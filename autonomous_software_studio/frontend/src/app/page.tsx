'use client'

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Activity,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  TrendingUp,
  Zap,
  Target,
  BarChart3,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { metricsApi, sessionsApi, queryKeys } from '@/lib/api'
import { cn, formatRelativeTime, getStatusColor, getStatusLabel } from '@/lib/utils'
import { Card, CardHeader, CardTitle, CardContent, Badge, Progress } from '@/components/ui'
import Link from 'next/link'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
}

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      duration: 0.5,
      ease: 'easeOut',
    },
  },
}

export default function DashboardPage() {
  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: queryKeys.metrics,
    queryFn: metricsApi.get,
    refetchInterval: 10000,
  })

  const { data: recentSessions } = useQuery({
    queryKey: queryKeys.sessions,
    queryFn: () => sessionsApi.list(),
    refetchInterval: 15000,
  })

  const statusData = metrics
    ? [
        { name: 'Running', value: metrics.running_sessions, color: '#00ffff' },
        { name: 'Awaiting', value: metrics.awaiting_approval, color: '#ff00ff' },
        { name: 'Completed', value: metrics.completed_sessions, color: '#00ff88' },
        { name: 'Failed', value: metrics.failed_sessions, color: '#ff4444' },
      ]
    : []

  const totalSessions = metrics?.total_sessions || 0
  const successRate = totalSessions > 0
    ? ((metrics?.completed_sessions || 0) / totalSessions * 100).toFixed(1)
    : '0'

  // Mock activity data for chart
  const activityData = [
    { time: '00:00', sessions: 2 },
    { time: '04:00', sessions: 4 },
    { time: '08:00', sessions: 8 },
    { time: '12:00', sessions: 15 },
    { time: '16:00', sessions: 12 },
    { time: '20:00', sessions: 6 },
    { time: '24:00', sessions: 3 },
  ]

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      {/* Page Header */}
      <motion.div variants={itemVariants} className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-foreground">
            <span className="text-neon-cyan">Command</span>{' '}
            <span className="text-foreground">Center</span>
          </h1>
          <p className="text-foreground-muted mt-1">
            Real-time overview of your autonomous software factory
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2 px-4 py-2 rounded-lg bg-background-secondary border border-border">
          <div className="h-2 w-2 rounded-full bg-neon-green animate-pulse" />
          <span className="text-sm text-foreground-muted">System Online</span>
        </div>
      </motion.div>

      {/* Key Metrics */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Sessions */}
        <Card glow className="relative overflow-hidden">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-foreground-muted uppercase tracking-wider">Total Sessions</p>
                <p className="text-4xl font-display font-bold text-foreground mt-2">
                  {metricsLoading ? '...' : metrics?.total_sessions || 0}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-neon-cyan/10 border border-neon-cyan/30">
                <BarChart3 className="h-6 w-6 text-neon-cyan" />
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2 text-sm">
              <TrendingUp className="h-4 w-4 text-neon-green" />
              <span className="text-neon-green">+12%</span>
              <span className="text-foreground-subtle">vs last week</span>
            </div>
          </CardContent>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-neon-cyan to-neon-magenta" />
        </Card>

        {/* Running */}
        <Card glow className="relative overflow-hidden">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-foreground-muted uppercase tracking-wider">Running</p>
                <p className="text-4xl font-display font-bold text-neon-cyan mt-2">
                  {metricsLoading ? '...' : metrics?.running_sessions || 0}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-neon-cyan/10 border border-neon-cyan/30">
                <Activity className="h-6 w-6 text-neon-cyan animate-pulse" />
              </div>
            </div>
            <div className="mt-4">
              <Progress value={30} className="h-2" />
            </div>
          </CardContent>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-neon-cyan" />
        </Card>

        {/* Awaiting Approval */}
        <Card glow className="relative overflow-hidden">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-foreground-muted uppercase tracking-wider">Awaiting Review</p>
                <p className="text-4xl font-display font-bold text-neon-magenta mt-2">
                  {metricsLoading ? '...' : metrics?.awaiting_approval || 0}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-neon-magenta/10 border border-neon-magenta/30">
                <Clock className="h-6 w-6 text-neon-magenta" />
              </div>
            </div>
            {(metrics?.awaiting_approval || 0) > 0 && (
              <Link
                href="/approvals"
                className="mt-4 inline-flex items-center gap-2 text-sm text-neon-magenta hover:underline"
              >
                <AlertCircle className="h-4 w-4" />
                Review pending sessions
              </Link>
            )}
          </CardContent>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-neon-magenta" />
        </Card>

        {/* Success Rate */}
        <Card glow className="relative overflow-hidden">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-foreground-muted uppercase tracking-wider">Success Rate</p>
                <p className="text-4xl font-display font-bold text-neon-green mt-2">
                  {successRate}%
                </p>
              </div>
              <div className="p-3 rounded-lg bg-neon-green/10 border border-neon-green/30">
                <Target className="h-6 w-6 text-neon-green" />
              </div>
            </div>
            <div className="mt-4 flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-neon-green" />
                <span className="text-foreground-muted">{metrics?.completed_sessions || 0} passed</span>
              </div>
              <div className="flex items-center gap-1.5">
                <XCircle className="h-4 w-4 text-red-400" />
                <span className="text-foreground-muted">{metrics?.failed_sessions || 0} failed</span>
              </div>
            </div>
          </CardContent>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-neon-green" />
        </Card>
      </motion.div>

      {/* Charts Row */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Chart */}
        <Card glow className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-neon-cyan" />
              Session Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={activityData}>
                  <defs>
                    <linearGradient id="colorSessions" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#00ffff" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#00ffff" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,100,150,0.2)" />
                  <XAxis
                    dataKey="time"
                    stroke="#6a6a7a"
                    tick={{ fill: '#a0a0b0', fontSize: 12 }}
                  />
                  <YAxis
                    stroke="#6a6a7a"
                    tick={{ fill: '#a0a0b0', fontSize: 12 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(20, 20, 30, 0.95)',
                      border: '1px solid rgba(100, 100, 150, 0.3)',
                      borderRadius: '8px',
                      color: '#e8e8f0',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="sessions"
                    stroke="#00ffff"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorSessions)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Status Distribution */}
        <Card glow>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-neon-magenta" />
              Status Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {statusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(20, 20, 30, 0.95)',
                      border: '1px solid rgba(100, 100, 150, 0.3)',
                      borderRadius: '8px',
                      color: '#e8e8f0',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {statusData.map((item) => (
                <div key={item.name} className="flex items-center gap-2">
                  <div
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-sm text-foreground-muted">{item.name}</span>
                  <span className="text-sm font-mono text-foreground ml-auto">
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Recent Sessions */}
      <motion.div variants={itemVariants}>
        <Card glow>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Sessions</CardTitle>
            <Link href="/sessions">
              <Badge variant="secondary" className="cursor-pointer hover:bg-background-tertiary">
                View All
              </Badge>
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentSessions?.slice(0, 5).map((session) => (
                <Link
                  key={session.session_id}
                  href={`/sessions/${session.session_id}`}
                  className="flex items-center justify-between p-4 rounded-lg bg-background-secondary/50 border border-border hover:border-neon-cyan/30 transition-all duration-300 group"
                >
                  <div className="flex items-center gap-4">
                    <div
                      className={cn(
                        'h-10 w-10 rounded-lg flex items-center justify-center',
                        'bg-gradient-to-br',
                        session.status === 'running' && 'from-neon-cyan/20 to-neon-blue/20 border border-neon-cyan/30',
                        session.status === 'awaiting_approval' && 'from-neon-magenta/20 to-neon-purple/20 border border-neon-magenta/30',
                        session.status === 'completed' && 'from-neon-green/20 to-neon-cyan/20 border border-neon-green/30',
                        session.status === 'failed' && 'from-red-500/20 to-neon-orange/20 border border-red-500/30',
                        session.status === 'pending' && 'from-neon-orange/20 to-neon-yellow/20 border border-neon-orange/30'
                      )}
                    >
                      {session.status === 'running' && <Activity className="h-5 w-5 text-neon-cyan animate-pulse" />}
                      {session.status === 'awaiting_approval' && <Clock className="h-5 w-5 text-neon-magenta" />}
                      {session.status === 'completed' && <CheckCircle2 className="h-5 w-5 text-neon-green" />}
                      {session.status === 'failed' && <XCircle className="h-5 w-5 text-red-400" />}
                      {session.status === 'pending' && <Clock className="h-5 w-5 text-neon-orange" />}
                    </div>
                    <div>
                      <p className="font-display font-medium text-foreground group-hover:text-neon-cyan transition-colors">
                        {session.project_name}
                      </p>
                      <p className="text-sm text-foreground-muted truncate max-w-md">
                        {session.mission}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
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
                    <span className="text-sm text-foreground-subtle">
                      {formatRelativeTime(session.updated_at)}
                    </span>
                  </div>
                </Link>
              ))}
              {(!recentSessions || recentSessions.length === 0) && (
                <div className="py-12 text-center">
                  <p className="text-foreground-muted">No sessions yet</p>
                  <p className="text-sm text-foreground-subtle mt-1">
                    Create your first session to get started
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Quick Stats */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-l-4 border-l-neon-cyan">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-foreground-muted">QA Pass Rate</p>
                <p className="text-2xl font-display font-bold text-neon-cyan mt-1">
                  {metrics?.qa_passed_count || 0}
                </p>
              </div>
              <CheckCircle2 className="h-8 w-8 text-neon-cyan/50" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-neon-magenta">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-foreground-muted">Avg QA Iterations</p>
                <p className="text-2xl font-display font-bold text-neon-magenta mt-1">
                  {metrics?.average_qa_iterations?.toFixed(1) || '0'}
                </p>
              </div>
              <Activity className="h-8 w-8 text-neon-magenta/50" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-neon-green">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-foreground-muted">Expired Sessions</p>
                <p className="text-2xl font-display font-bold text-foreground-muted mt-1">
                  {metrics?.expired_sessions || 0}
                </p>
              </div>
              <Clock className="h-8 w-8 text-foreground-subtle/50" />
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}
