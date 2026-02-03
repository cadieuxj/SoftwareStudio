'use client'

import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'react-hot-toast'
import {
  Github,
  Search,
  Star,
  GitFork,
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  GitPullRequest,
  Rocket,
  RefreshCw,
  Lock,
  Globe,
  Code,
} from 'lucide-react'
import { githubApi, queryKeys } from '@/lib/api'
import { cn, formatRelativeTime, truncate } from '@/lib/utils'
import { useGitHubStore, useCreateSessionModal } from '@/store'
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  Button,
  Input,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  ScrollArea,
} from '@/components/ui'

export default function GitHubPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const {
    selectedRepo,
    setSelectedRepo,
    isAuthenticated,
    username,
    setAuthenticated,
    selectedOrg,
    setSelectedOrg,
  } = useGitHubStore()
  const openCreateModal = useCreateSessionModal((s) => s.open)

  // Check auth status
  const { data: authStatus, isLoading: authLoading } = useQuery({
    queryKey: queryKeys.githubAuth,
    queryFn: githubApi.checkAuth,
    refetchOnMount: true,
    staleTime: 0,
  })

  // Update auth status
  useState(() => {
    if (authStatus) {
      setAuthenticated(authStatus.authenticated, authStatus.username)
    }
  })

  // Fetch repos
  const { data: repos = [], isLoading: reposLoading } = useQuery({
    queryKey: queryKeys.githubRepos(selectedOrg || undefined),
    queryFn: () => githubApi.listRepos(selectedOrg || undefined),
    enabled: authStatus?.authenticated || false,
  })

  // Fetch issues for selected repo
  const { data: issues = [] } = useQuery({
    queryKey: selectedRepo
      ? queryKeys.githubIssues(selectedRepo.owner, selectedRepo.name)
      : ['empty'],
    queryFn: () =>
      selectedRepo
        ? githubApi.listIssues(selectedRepo.owner, selectedRepo.name, 'open')
        : Promise.resolve([]),
    enabled: !!selectedRepo,
  })

  // Fetch PRs for selected repo
  const { data: prs = [] } = useQuery({
    queryKey: selectedRepo
      ? queryKeys.githubPRs(selectedRepo.owner, selectedRepo.name)
      : ['empty'],
    queryFn: () =>
      selectedRepo
        ? githubApi.listPRs(selectedRepo.owner, selectedRepo.name, 'open')
        : Promise.resolve([]),
    enabled: !!selectedRepo,
  })

  // Create session from issue
  const createFromIssueMutation = useMutation({
    mutationFn: ({ owner, repo, issueNumber }: { owner: string; repo: string; issueNumber: number }) =>
      githubApi.createSessionFromIssue(owner, repo, issueNumber),
    onSuccess: (session) => {
      toast.success(`Session created from issue!`)
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Failed to create session')
    },
  })

  // Filter repos
  const filteredRepos = repos.filter(
    (repo) =>
      repo.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      repo.description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (authLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="spinner h-12 w-12" />
      </div>
    )
  }

  if (!authStatus?.authenticated) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-3xl font-bold text-foreground">
            GitHub Integration
          </h1>
          <p className="text-foreground-muted mt-1">
            Connect your GitHub account to create sessions from issues
          </p>
        </div>

        <Card className="max-w-lg mx-auto">
          <CardContent className="py-12">
            <div className="text-center">
              <div className="inline-flex p-4 rounded-full bg-neon-magenta/10 border border-neon-magenta/30 mb-6">
                <Github className="h-12 w-12 text-neon-magenta" />
              </div>
              <h2 className="font-display text-2xl font-bold text-foreground mb-2">
                GitHub Not Connected
              </h2>
              <p className="text-foreground-muted mb-6">
                Authenticate with GitHub CLI to access your repositories and create
                sessions from issues.
              </p>
              <div className="bg-background-secondary rounded-lg p-4 text-left mb-6">
                <p className="text-sm text-foreground-muted mb-2">
                  Run this command in your terminal:
                </p>
                <code className="text-neon-cyan font-mono">gh auth login</code>
              </div>
              <Button
                variant="outline"
                onClick={() => window.location.reload()}
                className="gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Check Connection
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-foreground">
            GitHub Integration
          </h1>
          <p className="text-foreground-muted mt-1">
            Browse repositories and create sessions from issues
          </p>
        </div>
        <Badge variant="success" className="gap-2">
          <CheckCircle2 className="h-4 w-4" />
          Connected as {authStatus.username}
        </Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Repository List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Github className="h-5 w-5" />
              Repositories
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              placeholder="Search repositories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              icon={<Search className="h-4 w-4" />}
            />

            <ScrollArea className="h-[500px]">
              {reposLoading ? (
                <div className="flex items-center justify-center py-16">
                  <div className="spinner h-8 w-8" />
                </div>
              ) : (
                <div className="space-y-2 pr-4">
                  {filteredRepos.map((repo) => (
                    <div
                      key={repo.full_name}
                      className={cn(
                        'p-3 rounded-lg border cursor-pointer transition-all duration-300',
                        selectedRepo?.owner === repo.full_name.split('/')[0] &&
                          selectedRepo?.name === repo.name
                          ? 'border-neon-cyan bg-neon-cyan/10'
                          : 'border-border bg-background-secondary hover:border-neon-cyan/50'
                      )}
                      onClick={() =>
                        setSelectedRepo({
                          owner: repo.full_name.split('/')[0],
                          name: repo.name,
                        })
                      }
                    >
                      <div className="flex items-start gap-3">
                        {repo.private ? (
                          <Lock className="h-4 w-4 text-foreground-subtle shrink-0 mt-0.5" />
                        ) : (
                          <Globe className="h-4 w-4 text-foreground-subtle shrink-0 mt-0.5" />
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="font-display font-semibold text-foreground truncate">
                            {repo.name}
                          </p>
                          {repo.description && (
                            <p className="text-xs text-foreground-muted mt-1 line-clamp-2">
                              {repo.description}
                            </p>
                          )}
                          <div className="flex items-center gap-3 mt-2 text-xs text-foreground-subtle">
                            {repo.language && (
                              <span className="flex items-center gap-1">
                                <Code className="h-3 w-3" />
                                {repo.language}
                              </span>
                            )}
                            <span className="flex items-center gap-1">
                              <Star className="h-3 w-3" />
                              {repo.stargazers_count}
                            </span>
                            <span className="flex items-center gap-1">
                              <GitFork className="h-3 w-3" />
                              {repo.forks_count}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                  {filteredRepos.length === 0 && (
                    <div className="py-8 text-center text-foreground-muted text-sm">
                      No repositories found
                    </div>
                  )}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Repository Details */}
        <Card className="lg:col-span-2">
          {selectedRepo ? (
            <Tabs defaultValue="issues">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    {selectedRepo.owner}/{selectedRepo.name}
                    <a
                      href={`https://github.com/${selectedRepo.owner}/${selectedRepo.name}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-foreground-muted hover:text-neon-cyan"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </CardTitle>
                </div>
                <TabsList>
                  <TabsTrigger value="issues" className="gap-2">
                    <AlertCircle className="h-4 w-4" />
                    Issues ({issues.length})
                  </TabsTrigger>
                  <TabsTrigger value="prs" className="gap-2">
                    <GitPullRequest className="h-4 w-4" />
                    PRs ({prs.length})
                  </TabsTrigger>
                </TabsList>
              </CardHeader>
              <CardContent>
                <TabsContent value="issues">
                  <ScrollArea className="h-[450px]">
                    {issues.length > 0 ? (
                      <div className="space-y-3">
                        {issues.map((issue) => (
                          <div
                            key={issue.number}
                            className="p-4 rounded-lg bg-background-secondary border border-border hover:border-neon-cyan/30 transition-all duration-300"
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="text-foreground-muted">#{issue.number}</span>
                                  <a
                                    href={issue.html_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="font-display font-semibold text-foreground hover:text-neon-cyan transition-colors"
                                  >
                                    {issue.title}
                                  </a>
                                </div>
                                {issue.body && (
                                  <p className="text-sm text-foreground-muted line-clamp-2">
                                    {truncate(issue.body, 150)}
                                  </p>
                                )}
                                <div className="flex items-center gap-2 mt-2">
                                  {issue.labels.map((label) => (
                                    <Badge
                                      key={label.name}
                                      variant="secondary"
                                      size="sm"
                                      style={{
                                        backgroundColor: `#${label.color}20`,
                                        borderColor: `#${label.color}50`,
                                        color: `#${label.color}`,
                                      }}
                                    >
                                      {label.name}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                              <Button
                                size="sm"
                                onClick={() =>
                                  createFromIssueMutation.mutate({
                                    owner: selectedRepo.owner,
                                    repo: selectedRepo.name,
                                    issueNumber: issue.number,
                                  })
                                }
                                loading={createFromIssueMutation.isPending}
                                className="shrink-0 gap-2"
                              >
                                <Rocket className="h-4 w-4" />
                                Create Session
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="py-16 text-center text-foreground-muted">
                        No open issues
                      </div>
                    )}
                  </ScrollArea>
                </TabsContent>

                <TabsContent value="prs">
                  <ScrollArea className="h-[450px]">
                    {prs.length > 0 ? (
                      <div className="space-y-3">
                        {prs.map((pr) => (
                          <div
                            key={pr.number}
                            className="p-4 rounded-lg bg-background-secondary border border-border hover:border-neon-cyan/30 transition-all duration-300"
                          >
                            <div className="flex items-start gap-4">
                              <GitPullRequest
                                className={cn(
                                  'h-5 w-5 shrink-0 mt-0.5',
                                  pr.state === 'open' && 'text-neon-green',
                                  pr.state === 'closed' && 'text-red-400',
                                  pr.state === 'merged' && 'text-neon-magenta'
                                )}
                              />
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="text-foreground-muted">#{pr.number}</span>
                                  <a
                                    href={pr.html_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="font-display font-semibold text-foreground hover:text-neon-cyan transition-colors"
                                  >
                                    {pr.title}
                                  </a>
                                </div>
                                <div className="flex items-center gap-4 text-sm text-foreground-muted">
                                  <span>
                                    {pr.head.ref} → {pr.base.ref}
                                  </span>
                                  <span>{formatRelativeTime(pr.updated_at)}</span>
                                </div>
                              </div>
                              <Badge
                                variant={
                                  pr.state === 'open'
                                    ? 'success'
                                    : pr.state === 'merged'
                                    ? 'magenta'
                                    : 'error'
                                }
                              >
                                {pr.state}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="py-16 text-center text-foreground-muted">
                        No open pull requests
                      </div>
                    )}
                  </ScrollArea>
                </TabsContent>
              </CardContent>
            </Tabs>
          ) : (
            <CardContent className="py-16">
              <div className="text-center text-foreground-muted">
                <Github className="h-12 w-12 mx-auto mb-4 text-foreground-subtle" />
                <p>Select a repository to view issues and pull requests</p>
              </div>
            </CardContent>
          )}
        </Card>
      </div>
    </div>
  )
}
