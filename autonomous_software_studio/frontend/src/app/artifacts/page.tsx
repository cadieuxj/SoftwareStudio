'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import Link from 'next/link'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { toast } from 'react-hot-toast'
import {
  FileText,
  Code,
  Bug,
  Folder,
  Search,
  Copy,
  Download,
  ExternalLink,
  CheckCircle2,
  XCircle,
} from 'lucide-react'
import { sessionsApi, queryKeys } from '@/lib/api'
import { cn, formatRelativeTime, copyToClipboard, getStatusLabel } from '@/lib/utils'
import type { Session } from '@/types'
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
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  ScrollArea,
} from '@/components/ui'

export default function ArtifactsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSession, setSelectedSession] = useState<string>('')
  const [artifactType, setArtifactType] = useState<string>('prd')

  const { data: sessions = [] } = useQuery({
    queryKey: queryKeys.sessions,
    queryFn: () => sessionsApi.list(),
  })

  // Sessions with artifacts (completed or awaiting approval)
  const sessionsWithArtifacts = sessions.filter(
    (s) => s.status === 'completed' || s.status === 'awaiting_approval' || s.status === 'running'
  )

  const filteredSessions = sessionsWithArtifacts.filter(
    (s) =>
      s.project_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.mission.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const { data: artifacts, isLoading: artifactsLoading } = useQuery({
    queryKey: queryKeys.sessionArtifacts(selectedSession),
    queryFn: () => sessionsApi.getArtifacts(selectedSession),
    enabled: !!selectedSession,
  })

  const currentSession = sessions.find((s) => s.session_id === selectedSession)

  const handleCopy = async (content: string, label: string) => {
    const success = await copyToClipboard(content)
    if (success) {
      toast.success(`${label} copied to clipboard`)
    }
  }

  const handleDownload = (content: string, filename: string) => {
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
    toast.success(`Downloaded ${filename}`)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-foreground">
          Artifacts
        </h1>
        <p className="text-foreground-muted mt-1">
          Browse and review generated artifacts from your sessions
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Session List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Sessions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              placeholder="Search sessions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              icon={<Search className="h-4 w-4" />}
            />

            <ScrollArea className="h-[500px]">
              <div className="space-y-2 pr-4">
                {filteredSessions.map((session) => (
                  <div
                    key={session.session_id}
                    className={cn(
                      'p-3 rounded-lg border cursor-pointer transition-all duration-300',
                      selectedSession === session.session_id
                        ? 'border-neon-cyan bg-neon-cyan/10'
                        : 'border-border bg-background-secondary hover:border-neon-cyan/50'
                    )}
                    onClick={() => setSelectedSession(session.session_id)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="font-display font-semibold text-foreground truncate">
                          {session.project_name}
                        </p>
                        <p className="text-xs text-foreground-muted mt-1">
                          {formatRelativeTime(session.updated_at)}
                        </p>
                      </div>
                      {session.status === 'completed' ? (
                        <CheckCircle2 className="h-4 w-4 text-neon-green shrink-0" />
                      ) : (
                        <Badge variant="secondary" size="sm">
                          {getStatusLabel(session.status)}
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
                {filteredSessions.length === 0 && (
                  <div className="py-8 text-center text-foreground-muted text-sm">
                    No sessions with artifacts
                  </div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Artifact Viewer */}
        <Card className="lg:col-span-2">
          {selectedSession ? (
            <Tabs value={artifactType} onValueChange={setArtifactType}>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>{currentSession?.project_name}</CardTitle>
                  <p className="text-sm text-foreground-muted mt-1">
                    {currentSession?.mission.slice(0, 100)}...
                  </p>
                </div>
                <TabsList>
                  <TabsTrigger value="prd" className="gap-2">
                    <FileText className="h-4 w-4" />
                    PRD
                  </TabsTrigger>
                  <TabsTrigger value="tech_spec" className="gap-2">
                    <Code className="h-4 w-4" />
                    Spec
                  </TabsTrigger>
                  <TabsTrigger value="scaffold" className="gap-2">
                    <Folder className="h-4 w-4" />
                    Script
                  </TabsTrigger>
                  <TabsTrigger value="bugs" className="gap-2">
                    <Bug className="h-4 w-4" />
                    QA
                  </TabsTrigger>
                </TabsList>
              </CardHeader>
              <CardContent>
                {artifactsLoading ? (
                  <div className="flex items-center justify-center py-16">
                    <div className="spinner h-8 w-8" />
                  </div>
                ) : (
                  <>
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
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDownload(artifacts.prd!, 'PRD.md')}
                            >
                              <Download className="h-4 w-4 mr-2" />
                              Download
                            </Button>
                          </div>
                          <ScrollArea className="h-[450px] rounded-lg border border-border bg-background-secondary p-6">
                            <div className="markdown-content">
                              <ReactMarkdown>{artifacts.prd}</ReactMarkdown>
                            </div>
                          </ScrollArea>
                        </div>
                      ) : (
                        <div className="py-16 text-center text-foreground-muted">
                          No PRD available
                        </div>
                      )}
                    </TabsContent>

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
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDownload(artifacts.tech_spec!, 'TECH_SPEC.md')}
                            >
                              <Download className="h-4 w-4 mr-2" />
                              Download
                            </Button>
                          </div>
                          <ScrollArea className="h-[450px] rounded-lg border border-border bg-background-secondary p-6">
                            <div className="markdown-content">
                              <ReactMarkdown>{artifacts.tech_spec}</ReactMarkdown>
                            </div>
                          </ScrollArea>
                        </div>
                      ) : (
                        <div className="py-16 text-center text-foreground-muted">
                          No Tech Spec available
                        </div>
                      )}
                    </TabsContent>

                    <TabsContent value="scaffold">
                      {artifacts?.scaffold_script ? (
                        <div className="space-y-4">
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleCopy(artifacts.scaffold_script!, 'Script')}
                            >
                              <Copy className="h-4 w-4 mr-2" />
                              Copy
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDownload(artifacts.scaffold_script!, 'scaffold.sh')}
                            >
                              <Download className="h-4 w-4 mr-2" />
                              Download
                            </Button>
                          </div>
                          <ScrollArea className="h-[450px] rounded-lg border border-border bg-background-secondary">
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
                        <div className="py-16 text-center text-foreground-muted">
                          No scaffold script available
                        </div>
                      )}
                    </TabsContent>

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
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDownload(artifacts.bug_report!, 'BUG_REPORT.md')}
                            >
                              <Download className="h-4 w-4 mr-2" />
                              Download
                            </Button>
                          </div>
                          <ScrollArea className="h-[450px] rounded-lg border border-border bg-background-secondary p-6">
                            <div className="markdown-content">
                              <ReactMarkdown>{artifacts.bug_report}</ReactMarkdown>
                            </div>
                          </ScrollArea>
                        </div>
                      ) : (
                        <div className="py-16 text-center text-foreground-muted">
                          No QA report available
                        </div>
                      )}
                    </TabsContent>
                  </>
                )}
              </CardContent>
            </Tabs>
          ) : (
            <CardContent className="py-16">
              <div className="text-center text-foreground-muted">
                <Folder className="h-12 w-12 mx-auto mb-4 text-foreground-subtle" />
                <p>Select a session to view its artifacts</p>
              </div>
            </CardContent>
          )}
        </Card>
      </div>
    </div>
  )
}
