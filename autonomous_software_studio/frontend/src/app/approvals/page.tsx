'use client'

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import Link from 'next/link'
import {
  AlertCircle,
  Clock,
  ArrowRight,
  FileText,
  Code,
  Eye,
} from 'lucide-react'
import { sessionsApi, queryKeys } from '@/lib/api'
import { cn, formatRelativeTime, getPhaseLabel, truncate } from '@/lib/utils'
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  Button,
} from '@/components/ui'

export default function ApprovalsPage() {
  const { data: sessions = [], isLoading } = useQuery({
    queryKey: queryKeys.sessions,
    queryFn: () => sessionsApi.list('awaiting_approval'),
    refetchInterval: 10000,
  })

  const awaitingSessions = sessions.filter((s) => s.status === 'awaiting_approval')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-foreground">
            Pending Approvals
          </h1>
          <p className="text-foreground-muted mt-1">
            Review and approve sessions awaiting your feedback
          </p>
        </div>
        <Badge
          variant={awaitingSessions.length > 0 ? 'awaiting' : 'secondary'}
          className="gap-2"
        >
          <AlertCircle className="h-4 w-4" />
          {awaitingSessions.length} pending
        </Badge>
      </div>

      {/* Pending Sessions */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="spinner h-8 w-8" />
        </div>
      ) : awaitingSessions.length > 0 ? (
        <div className="grid gap-6">
          {awaitingSessions.map((session, idx) => (
            <motion.div
              key={session.session_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
            >
              <Card className="border-neon-magenta/30 hover:border-neon-magenta/50 transition-all duration-300">
                <CardContent className="pt-6">
                  <div className="flex flex-col lg:flex-row lg:items-center gap-6">
                    {/* Session Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 rounded-lg bg-neon-magenta/10 border border-neon-magenta/30">
                          <AlertCircle className="h-5 w-5 text-neon-magenta" />
                        </div>
                        <div>
                          <h3 className="font-display text-xl font-semibold text-foreground">
                            {session.project_name}
                          </h3>
                          <div className="flex items-center gap-2 text-sm text-foreground-muted">
                            <Clock className="h-4 w-4" />
                            Waiting {formatRelativeTime(session.updated_at)}
                          </div>
                        </div>
                      </div>
                      <p className="text-foreground-muted mt-3">
                        {truncate(session.mission, 200)}
                      </p>
                    </div>

                    {/* Phase & Actions */}
                    <div className="flex flex-col sm:flex-row lg:flex-col xl:flex-row items-start gap-4">
                      {/* Available Artifacts */}
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="secondary" className="gap-1.5">
                          <FileText className="h-3 w-3" />
                          PRD Ready
                        </Badge>
                        <Badge variant="secondary" className="gap-1.5">
                          <Code className="h-3 w-3" />
                          Tech Spec Ready
                        </Badge>
                      </div>

                      {/* Review Button */}
                      <Link href={`/sessions/${session.session_id}`}>
                        <Button className="gap-2 whitespace-nowrap">
                          <Eye className="h-4 w-4" />
                          Review & Approve
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </Link>
                    </div>
                  </div>

                  {/* Phase Progress */}
                  <div className="mt-6 pt-4 border-t border-border">
                    <div className="flex items-center gap-4">
                      {['pm', 'arch', 'human_gate', 'engineer', 'qa', 'complete'].map((phase, i) => {
                        const currentPhaseIdx = ['pm', 'arch', 'human_gate', 'engineer', 'qa', 'complete'].indexOf(session.phase)
                        const isActive = phase === session.phase
                        const isCompleted = i < currentPhaseIdx

                        return (
                          <div key={phase} className="flex items-center gap-2">
                            <div
                              className={cn(
                                'h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold',
                                isActive && 'bg-neon-magenta/20 border-2 border-neon-magenta text-neon-magenta',
                                isCompleted && 'bg-neon-green/20 border-2 border-neon-green text-neon-green',
                                !isActive && !isCompleted && 'bg-background-tertiary border-2 border-border text-foreground-subtle'
                              )}
                            >
                              {i + 1}
                            </div>
                            {i < 5 && (
                              <div
                                className={cn(
                                  'hidden sm:block w-8 h-0.5',
                                  isCompleted ? 'bg-neon-green' : 'bg-border'
                                )}
                              />
                            )}
                          </div>
                        )
                      })}
                    </div>
                    <div className="flex items-center gap-4 mt-2">
                      {['PM', 'Arch', 'Review', 'Eng', 'QA', 'Done'].map((label, i) => (
                        <span key={label} className="text-xs text-foreground-subtle w-8 text-center">
                          {label}
                        </span>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-16">
            <div className="text-center">
              <div className="inline-flex p-4 rounded-full bg-neon-green/10 border border-neon-green/30 mb-4">
                <AlertCircle className="h-8 w-8 text-neon-green" />
              </div>
              <h3 className="font-display text-xl font-semibold text-foreground">
                All Caught Up!
              </h3>
              <p className="text-foreground-muted mt-2">
                No sessions are waiting for your approval.
              </p>
              <Link href="/sessions">
                <Button variant="outline" className="mt-6">
                  View All Sessions
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
