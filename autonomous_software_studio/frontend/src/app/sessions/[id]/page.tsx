'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'react-hot-toast'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import {
  ArrowLeft,
  Activity,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  FileText,
  Code,
  Bug,
  Folder,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
  Send,
  Copy,
  Download,
} from 'lucide-react'
import Link from 'next/link'
import { sessionsApi, queryKeys } from '@/lib/api'
import {
  cn,
  formatDateTime,
  formatRelativeTime,
  getStatusLabel,
  getPhaseLabel,
  copyToClipboard,
} from '@/lib/utils'
import type { SessionPhase } from '@/types'
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  Button,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  Textarea,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  ScrollArea,
  Progress,
} from '@/components/ui'

export default function SessionDetailPage() {
  const params = useParams()
  const router = useRouter()
  const sessionId = params.id as string
  const queryClient = useQueryClient()

  const [feedback, setFeedback] = useState('')
  const [rejectPhase, setRejectPhase] = useState<SessionPhase>('pm')

  const { data: session, isLoading: sessionLoading } = useQuery({
    queryKey: queryKeys.session(sessionId),
    queryFn: () => sessionsApi.get(sessionId),
    refetchInterval: 5000,
  })

  const { data: artifacts, isLoading: artifactsLoading } = useQuery({
    queryKey: queryKeys.sessionArtifacts(sessionId),
    queryFn: () => sessionsApi.getArtifacts(sessionId),
    enabled: !!session,
  })

  const { data: logs } = useQuery({
    queryKey: queryKeys.sessionLogs(sessionId),
    queryFn: () => sessionsApi.getLogs(sessionId, 50),
    refetchInterval: session?.status === 'running' ? 3000 : false,
  })

  const approveMutation = useMutation({
    mutationFn: () => sessionsApi.approve(sessionId),
    onSuccess: () => {
      toast.success('Session approved! Continuing to engineering...')
      queryClient.invalidateQueries({ queryKey: queryKeys.session(sessionId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions })
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Failed to approve session')
    },
  })

  const rejectMutation = useMutation({
    mutationFn: () => sessionsApi.reject(sessionId, { feedback, reject_phase: rejectPhase }),
    onSuccess: () => {
      toast.success('Feedback sent! Session returning for revision...')
      setFeedback('')
      queryClient.invalidateQueries({ queryKey: queryKeys.session(sessionId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions })
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Failed to reject session')
    },
  })

  if (sessionLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="spinner h-12 w-12" />
      </div>
    )
  }

  if (!session) {
    return (
      <div className="py-16 text-center">
        <h2 className="text-xl font-display text-foreground">Session not found</h2>
        <Button variant="outline" className="mt-4" onClick={() => router.push('/sessions')}>
          Back to Sessions
        </Button>
      </div>
    )
  }

  const StatusIcon = {
    pending: Clock,
    running: Activity,
    awaiting_approval: AlertCircle,
    completed: CheckCircle2,
    failed: XCircle,
    expired: Clock,
  }[session.status]

  const handleCopy = async (content: string, label: string) => {
    const success = await copyToClipboard(content)
    if (success) {
      toast.success(`${label} copied to clipboard`)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <Link href="/sessions">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div>
            <h1 className="font-display text-2xl font-bold text-foreground">
              {session.project_name}
            </h1>
            <p className="text-foreground-muted mt-1 max-w-2xl">
              {session.mission}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Badge
            variant={
              session.status === 'running' ? 'running' :
              session.status === 'awaiting_approval' ? 'awaiting' :
              session.status === 'completed' ? 'completed' :
              session.status === 'failed' ? 'failed' :
              'pending'
            }
            className="gap-2"
          >
            <StatusIcon className={cn(
              'h-4 w-4',
              session.status === 'running' && 'animate-pulse'
            )} />
            {getStatusLabel(session.status)}
          </Badge>
        </div>
      </div>

      {/* Status Bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p className="text-sm text-foreground-muted">Current Phase</p>
              <p className="font-display font-semibold text-neon-cyan mt-1">
                {getPhaseLabel(session.phase)}
              </p>
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Iterations</p>
              <p className="font-display font-semibold text-foreground mt-1">
                {session.iteration_count}
              </p>
            </div>
            <div>
              <p className="text-sm text-foreground-muted">QA Status</p>
              <p className={cn(
                'font-display font-semibold mt-1',
                session.qa_passed ? 'text-neon-green' : 'text-foreground-muted'
              )}>
                {session.qa_passed ? 'Passed' : 'Pending'}
              </p>
            </div>
            <div>
              <p className="text-sm text-foreground-muted">Last Updated</p>
              <p className="font-display font-semibold text-foreground mt-1">
                {formatRelativeTime(session.updated_at)}
              </p>
            </div>
          </div>

          {session.status === 'running' && (
            <div className="mt-6">
              <Progress value={60} className="h-2" />
              <p className="text-xs text-foreground-muted mt-2">
                Processing in {getPhaseLabel(session.phase)}...
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Approval Panel */}
      {session.status === 'awaiting_approval' && (
        <Card className="border-neon-magenta/50 bg-neon-magenta/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-neon-magenta">
              <AlertCircle className="h-5 w-5" />
              Approval Required
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <p className="text-foreground-muted">
              Review the generated artifacts below and approve to continue to the engineering phase,
              or provide feedback to request changes.
            </p>

            <div className="flex flex-col lg:flex-row gap-4">
              {/* Approve */}
              <Button
                variant="success"
                onClick={() => approveMutation.mutate()}
                loading={approveMutation.isPending}
                className="gap-2"
              >
                <ThumbsUp className="h-4 w-4" />
                Approve & Build
              </Button>

              {/* Reject with Feedback */}
              <div className="flex-1 space-y-3">
                <div className="flex gap-3">
                  <Textarea
                    placeholder="Provide feedback for changes..."
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    className="flex-1 min-h-[80px]"
                  />
                </div>
                <div className="flex gap-3">
                  <Select
                    value={rejectPhase}
                    onValueChange={(v) => setRejectPhase(v as SessionPhase)}
                  >
                    <SelectTrigger className="w-[200px]">
                      <SelectValue placeholder="Send back to..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pm">Product Manager</SelectItem>
                      <SelectItem value="arch">Architect</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    variant="destructive"
                    onClick={() => rejectMutation.mutate()}
                    loading={rejectMutation.isPending}
                    disabled={!feedback.trim()}
                    className="gap-2"
                  >
                    <Send className="h-4 w-4" />
                    Request Changes
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Artifacts Tabs */}
      <Card>
        <Tabs defaultValue="prd">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Artifacts</CardTitle>
              <TabsList>
                <TabsTrigger value="prd" className="gap-2">
                  <FileText className="h-4 w-4" />
                  PRD
                </TabsTrigger>
                <TabsTrigger value="tech_spec" className="gap-2">
                  <Code className="h-4 w-4" />
                  Tech Spec
                </TabsTrigger>
                <TabsTrigger value="scaffold" className="gap-2">
                  <Folder className="h-4 w-4" />
                  Scaffold
                </TabsTrigger>
                <TabsTrigger value="bugs" className="gap-2">
                  <Bug className="h-4 w-4" />
                  QA Report
                </TabsTrigger>
                <TabsTrigger value="files" className="gap-2">
                  <Folder className="h-4 w-4" />
                  Files
                </TabsTrigger>
              </TabsList>
            </div>
          </CardHeader>
          <CardContent>
            {artifactsLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="spinner h-8 w-8" />
              </div>
            ) : (
              <>
                {/* PRD */}
                <TabsContent value="prd">
                  {artifacts?.prd ? (
                    <div className="space-y-4">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCopy(artifacts.prd!, 'PRD')}
                        >
                          <Copy className="h-4 w-4 mr-2" />
                          Copy
                        </Button>
                      </div>
                      <ScrollArea className="h-[500px] rounded-lg border border-border bg-background-secondary p-6">
                        <div className="markdown-content">
                          <ReactMarkdown>{artifacts.prd}</ReactMarkdown>
                        </div>
                      </ScrollArea>
                    </div>
                  ) : (
                    <div className="py-12 text-center text-foreground-muted">
                      No PRD generated yet
                    </div>
                  )}
                </TabsContent>

                {/* Tech Spec */}
                <TabsContent value="tech_spec">
                  {artifacts?.tech_spec ? (
                    <div className="space-y-4">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCopy(artifacts.tech_spec!, 'Tech Spec')}
                        >
                          <Copy className="h-4 w-4 mr-2" />
                          Copy
                        </Button>
                      </div>
                      <ScrollArea className="h-[500px] rounded-lg border border-border bg-background-secondary p-6">
                        <div className="markdown-content">
                          <ReactMarkdown>{artifacts.tech_spec}</ReactMarkdown>
                        </div>
                      </ScrollArea>
                    </div>
                  ) : (
                    <div className="py-12 text-center text-foreground-muted">
                      No Tech Spec generated yet
                    </div>
                  )}
                </TabsContent>

                {/* Scaffold Script */}
                <TabsContent value="scaffold">
                  {artifacts?.scaffold_script ? (
                    <div className="space-y-4">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCopy(artifacts.scaffold_script!, 'Scaffold Script')}
                        >
                          <Copy className="h-4 w-4 mr-2" />
                          Copy
                        </Button>
                      </div>
                      <ScrollArea className="h-[500px] rounded-lg border border-border bg-background-secondary">
                        <SyntaxHighlighter
                          language="bash"
                          style={vscDarkPlus}
                          customStyle={{
                            margin: 0,
                            padding: '1.5rem',
                            background: 'transparent',
                          }}
                        >
                          {artifacts.scaffold_script}
                        </SyntaxHighlighter>
                      </ScrollArea>
                    </div>
                  ) : (
                    <div className="py-12 text-center text-foreground-muted">
                      No scaffold script generated yet
                    </div>
                  )}
                </TabsContent>

                {/* Bug Report */}
                <TabsContent value="bugs">
                  {artifacts?.bug_report ? (
                    <div className="space-y-4">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCopy(artifacts.bug_report!, 'Bug Report')}
                        >
                          <Copy className="h-4 w-4 mr-2" />
                          Copy
                        </Button>
                      </div>
                      <ScrollArea className="h-[500px] rounded-lg border border-border bg-background-secondary p-6">
                        <div className="markdown-content">
                          <ReactMarkdown>{artifacts.bug_report}</ReactMarkdown>
                        </div>
                      </ScrollArea>
                    </div>
                  ) : (
                    <div className="py-12 text-center text-foreground-muted">
                      No QA report yet
                    </div>
                  )}
                </TabsContent>

                {/* Files Created */}
                <TabsContent value="files">
                  {artifacts?.files_created && artifacts.files_created.length > 0 ? (
                    <ScrollArea className="h-[500px]">
                      <div className="space-y-2">
                        {artifacts.files_created.map((file, idx) => (
                          <div
                            key={idx}
                            className="flex items-center gap-3 p-3 rounded-lg bg-background-secondary border border-border"
                          >
                            <Code className="h-4 w-4 text-neon-cyan" />
                            <span className="font-mono text-sm text-foreground">{file}</span>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  ) : (
                    <div className="py-12 text-center text-foreground-muted">
                      No files created yet
                    </div>
                  )}
                </TabsContent>
              </>
            )}
          </CardContent>
        </Tabs>
      </Card>

      {/* Live Logs */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-neon-cyan" />
            Execution Logs
          </CardTitle>
          <Button variant="outline" size="sm" onClick={() => queryClient.invalidateQueries({ queryKey: queryKeys.sessionLogs(sessionId) })}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[300px] rounded-lg border border-border bg-background-secondary p-4">
            {logs && logs.length > 0 ? (
              <div className="space-y-1 font-mono text-sm">
                {logs.map((log, idx) => (
                  <div key={idx} className="flex gap-3">
                    <span className="text-foreground-subtle shrink-0">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>
                    <span className={cn(
                      'uppercase text-xs font-semibold shrink-0 w-16',
                      log.level === 'error' && 'text-red-400',
                      log.level === 'warning' && 'text-neon-orange',
                      log.level === 'info' && 'text-neon-cyan',
                      log.level === 'debug' && 'text-foreground-subtle'
                    )}>
                      [{log.level}]
                    </span>
                    {log.agent && (
                      <span className="text-neon-magenta shrink-0">
                        [{log.agent}]
                      </span>
                    )}
                    <span className="text-foreground">{log.message}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-8 text-center text-foreground-muted">
                No logs available
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Session Info */}
      <Card>
        <CardHeader>
          <CardTitle>Session Details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <dt className="text-sm text-foreground-muted">Session ID</dt>
              <dd className="font-mono text-sm text-foreground mt-1">{session.session_id}</dd>
            </div>
            <div>
              <dt className="text-sm text-foreground-muted">Work Directory</dt>
              <dd className="font-mono text-sm text-foreground mt-1">{session.work_dir || 'N/A'}</dd>
            </div>
            <div>
              <dt className="text-sm text-foreground-muted">Created</dt>
              <dd className="text-sm text-foreground mt-1">{formatDateTime(session.created_at)}</dd>
            </div>
            <div>
              <dt className="text-sm text-foreground-muted">Last Updated</dt>
              <dd className="text-sm text-foreground mt-1">{formatDateTime(session.updated_at)}</dd>
            </div>
          </dl>

          {session.errors && session.errors.length > 0 && (
            <div className="mt-6">
              <h4 className="text-sm font-semibold text-red-400 mb-2">Errors</h4>
              <div className="space-y-2">
                {session.errors.map((error, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400"
                  >
                    {error}
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
