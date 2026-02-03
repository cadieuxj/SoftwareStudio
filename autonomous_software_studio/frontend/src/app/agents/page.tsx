'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-hot-toast'
import {
  Bot,
  Save,
  RotateCcw,
  History,
  Plus,
  Trash2,
  Key,
  Settings,
  FileText,
  Cpu,
  Clock,
  AlertCircle,
} from 'lucide-react'
import { agentSettingsApi, queryKeys } from '@/lib/api'
import { cn, getAgentLabel, getAgentColor, formatDateTime } from '@/lib/utils'
import { useAgentSettingsStore } from '@/store'
import type { AgentRole, AgentSettings, Provider, AuthType, UsageLimitUnit, PromptVersion } from '@/types'
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  Button,
  Input,
  Textarea,
  Switch,
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
  Label,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui'

const PROVIDERS: { value: Provider; label: string }[] = [
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'claude_code', label: 'Claude Code CLI' },
  { value: 'groq', label: 'Groq' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'azure_openai', label: 'Azure OpenAI' },
  { value: 'custom', label: 'Custom' },
]

const AUTH_TYPES: { value: AuthType; label: string }[] = [
  { value: 'api_key', label: 'API Key' },
  { value: 'token', label: 'Auth Token' },
  { value: 'none', label: 'None' },
]

const USAGE_UNITS: { value: UsageLimitUnit; label: string }[] = [
  { value: 'runs', label: 'Runs' },
  { value: 'sessions', label: 'Sessions' },
  { value: 'minutes', label: 'Minutes' },
]

const AGENTS: AgentRole[] = ['pm', 'architect', 'engineer', 'qa']

export default function AgentsPage() {
  const queryClient = useQueryClient()
  const {
    selectedAgent,
    setSelectedAgent,
    promptEditorContent,
    setPromptEditorContent,
    promptEditorDirty,
    setPromptEditorDirty,
  } = useAgentSettingsStore()

  const [settings, setSettings] = useState<Partial<AgentSettings>>({})
  const [customEnvVars, setCustomEnvVars] = useState<Array<{ key: string; value: string }>>([])
  const [promptNote, setPromptNote] = useState('')
  const [showHistoryDialog, setShowHistoryDialog] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<PromptVersion | null>(null)

  // Fetch all agent settings
  const { data: allSettings } = useQuery({
    queryKey: queryKeys.agentSettings,
    queryFn: agentSettingsApi.getAll,
  })

  // Fetch current agent settings
  const { data: agentSettings, isLoading: settingsLoading } = useQuery({
    queryKey: queryKeys.agentSetting(selectedAgent),
    queryFn: () => agentSettingsApi.get(selectedAgent),
  })

  // Fetch active prompt
  const { data: activePrompt } = useQuery({
    queryKey: queryKeys.agentActivePrompt(selectedAgent),
    queryFn: () => agentSettingsApi.getActivePrompt(selectedAgent),
  })

  // Fetch prompt history
  const { data: promptHistory = [] } = useQuery({
    queryKey: queryKeys.agentPromptHistory(selectedAgent),
    queryFn: () => agentSettingsApi.getPromptHistory(selectedAgent),
  })

  // Update local state when settings load
  useEffect(() => {
    if (agentSettings) {
      setSettings(agentSettings)
      setCustomEnvVars(
        Object.entries(agentSettings.custom_env_vars || {}).map(([key, value]) => ({
          key,
          value,
        }))
      )
    }
  }, [agentSettings])

  // Update prompt content when active prompt loads
  useEffect(() => {
    if (activePrompt) {
      setPromptEditorContent(activePrompt.content)
      setPromptEditorDirty(false)
    }
  }, [activePrompt, setPromptEditorContent, setPromptEditorDirty])

  // Save settings mutation
  const saveMutation = useMutation({
    mutationFn: (updates: Partial<AgentSettings>) =>
      agentSettingsApi.update(selectedAgent, {
        ...updates,
        custom_env_vars: customEnvVars.reduce(
          (acc, { key, value }) => {
            if (key) acc[key] = value
            return acc
          },
          {} as Record<string, string>
        ),
      }),
    onSuccess: () => {
      toast.success('Agent settings saved')
      queryClient.invalidateQueries({ queryKey: queryKeys.agentSetting(selectedAgent) })
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Failed to save settings')
    },
  })

  // Reset usage mutation
  const resetUsageMutation = useMutation({
    mutationFn: () => agentSettingsApi.resetUsage(selectedAgent),
    onSuccess: () => {
      toast.success('Usage counter reset')
      queryClient.invalidateQueries({ queryKey: queryKeys.agentSetting(selectedAgent) })
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Failed to reset usage')
    },
  })

  // Save prompt version mutation
  const savePromptMutation = useMutation({
    mutationFn: () =>
      agentSettingsApi.savePromptVersion(selectedAgent, promptEditorContent, promptNote),
    onSuccess: () => {
      toast.success('Prompt version saved')
      setPromptNote('')
      setPromptEditorDirty(false)
      queryClient.invalidateQueries({ queryKey: queryKeys.agentActivePrompt(selectedAgent) })
      queryClient.invalidateQueries({ queryKey: queryKeys.agentPromptHistory(selectedAgent) })
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Failed to save prompt')
    },
  })

  // Revert prompt mutation
  const revertPromptMutation = useMutation({
    mutationFn: (path: string) => agentSettingsApi.revertPrompt(selectedAgent, path),
    onSuccess: () => {
      toast.success('Prompt reverted')
      setShowHistoryDialog(false)
      queryClient.invalidateQueries({ queryKey: queryKeys.agentActivePrompt(selectedAgent) })
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Failed to revert prompt')
    },
  })

  // Reset to default prompt mutation
  const resetPromptMutation = useMutation({
    mutationFn: () => agentSettingsApi.resetPromptToDefault(selectedAgent),
    onSuccess: () => {
      toast.success('Prompt reset to default')
      queryClient.invalidateQueries({ queryKey: queryKeys.agentActivePrompt(selectedAgent) })
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Failed to reset prompt')
    },
  })

  const handleSave = () => {
    saveMutation.mutate(settings)
  }

  const addEnvVar = () => {
    setCustomEnvVars([...customEnvVars, { key: '', value: '' }])
  }

  const removeEnvVar = (index: number) => {
    setCustomEnvVars(customEnvVars.filter((_, i) => i !== index))
  }

  const updateEnvVar = (index: number, field: 'key' | 'value', value: string) => {
    const updated = [...customEnvVars]
    updated[index][field] = value
    setCustomEnvVars(updated)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-foreground">
          Agent Configuration
        </h1>
        <p className="text-foreground-muted mt-1">
          Configure AI agents, credentials, usage limits, and prompts
        </p>
      </div>

      {/* Agent Tabs */}
      <Tabs
        value={selectedAgent}
        onValueChange={(v) => setSelectedAgent(v as AgentRole)}
      >
        <TabsList className="w-full justify-start">
          {AGENTS.map((agent) => (
            <TabsTrigger
              key={agent}
              value={agent}
              className="gap-2 flex-1 max-w-[200px]"
            >
              <Bot className={cn('h-4 w-4', getAgentColor(agent))} />
              {getAgentLabel(agent)}
            </TabsTrigger>
          ))}
        </TabsList>

        {AGENTS.map((agent) => (
          <TabsContent key={agent} value={agent} className="mt-6">
            {settingsLoading ? (
              <div className="flex items-center justify-center py-16">
                <div className="spinner h-8 w-8" />
              </div>
            ) : (
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                {/* Account Settings */}
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <Settings className="h-5 w-5 text-neon-cyan" />
                      Account Settings
                    </CardTitle>
                    <Button
                      onClick={handleSave}
                      loading={saveMutation.isPending}
                      className="gap-2"
                    >
                      <Save className="h-4 w-4" />
                      Save
                    </Button>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Provider & Model */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Provider</Label>
                        <Select
                          value={settings.provider || 'anthropic'}
                          onValueChange={(v) =>
                            setSettings({ ...settings, provider: v as Provider })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {PROVIDERS.map((p) => (
                              <SelectItem key={p.value} value={p.value}>
                                {p.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Model</Label>
                        <Input
                          placeholder="claude-3-5-sonnet-20241022"
                          value={settings.model || ''}
                          onChange={(e) =>
                            setSettings({ ...settings, model: e.target.value })
                          }
                        />
                      </div>
                    </div>

                    {/* Auth */}
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label>Authentication Type</Label>
                        <Select
                          value={settings.auth_type || 'api_key'}
                          onValueChange={(v) =>
                            setSettings({ ...settings, auth_type: v as AuthType })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {AUTH_TYPES.map((a) => (
                              <SelectItem key={a.value} value={a.value}>
                                {a.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      {settings.auth_type === 'api_key' && (
                        <div className="space-y-2">
                          <Label>API Key</Label>
                          <Input
                            type="password"
                            placeholder="sk-..."
                            value={settings.api_key || ''}
                            onChange={(e) =>
                              setSettings({ ...settings, api_key: e.target.value })
                            }
                            icon={<Key className="h-4 w-4" />}
                          />
                        </div>
                      )}

                      {settings.auth_type === 'token' && (
                        <>
                          <div className="space-y-2">
                            <Label>Auth Token</Label>
                            <Input
                              type="password"
                              placeholder="Token"
                              value={settings.auth_token || ''}
                              onChange={(e) =>
                                setSettings({ ...settings, auth_token: e.target.value })
                              }
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Token Environment Variable</Label>
                            <Input
                              placeholder="ANTHROPIC_API_KEY"
                              value={settings.auth_token_env_var || ''}
                              onChange={(e) =>
                                setSettings({ ...settings, auth_token_env_var: e.target.value })
                              }
                            />
                          </div>
                        </>
                      )}
                    </div>

                    {/* Additional Settings */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Account Label</Label>
                        <Input
                          placeholder="Production"
                          value={settings.account_label || ''}
                          onChange={(e) =>
                            setSettings({ ...settings, account_label: e.target.value })
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Claude Profile Directory</Label>
                        <Input
                          placeholder="~/.claude"
                          value={settings.claude_profile_dir || ''}
                          onChange={(e) =>
                            setSettings({ ...settings, claude_profile_dir: e.target.value })
                          }
                        />
                      </div>
                    </div>

                    {/* Usage Limits */}
                    <div className="space-y-4">
                      <h4 className="font-display font-semibold text-foreground flex items-center gap-2">
                        <Clock className="h-4 w-4 text-neon-magenta" />
                        Usage Limits
                      </h4>
                      <div className="grid grid-cols-3 gap-4">
                        <div className="space-y-2">
                          <Label>Daily Limit</Label>
                          <Input
                            type="number"
                            placeholder="100"
                            value={settings.daily_limit || ''}
                            onChange={(e) =>
                              setSettings({
                                ...settings,
                                daily_limit: parseInt(e.target.value) || undefined,
                              })
                            }
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Unit</Label>
                          <Select
                            value={settings.daily_limit_unit || 'runs'}
                            onValueChange={(v) =>
                              setSettings({
                                ...settings,
                                daily_limit_unit: v as UsageLimitUnit,
                              })
                            }
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {USAGE_UNITS.map((u) => (
                                <SelectItem key={u.value} value={u.value}>
                                  {u.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="flex items-end">
                          <div className="flex items-center gap-2 p-3 rounded-lg bg-background-secondary border border-border w-full">
                            <Switch
                              checked={settings.hard_limit || false}
                              onCheckedChange={(checked) =>
                                setSettings({ ...settings, hard_limit: checked })
                              }
                            />
                            <Label className="text-sm">Hard Limit</Label>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-4 rounded-lg bg-background-secondary border border-border">
                        <div>
                          <p className="text-sm text-foreground">Usage Today</p>
                          <p className="text-2xl font-display font-bold text-neon-cyan">
                            {settings.usage_today || 0}
                          </p>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => resetUsageMutation.mutate()}
                          loading={resetUsageMutation.isPending}
                        >
                          <RotateCcw className="h-4 w-4 mr-2" />
                          Reset
                        </Button>
                      </div>
                    </div>

                    {/* Custom Environment Variables */}
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="font-display font-semibold text-foreground">
                          Custom Environment Variables
                        </h4>
                        <Button variant="outline" size="sm" onClick={addEnvVar}>
                          <Plus className="h-4 w-4 mr-2" />
                          Add
                        </Button>
                      </div>
                      <div className="space-y-2">
                        {customEnvVars.map((env, idx) => (
                          <div key={idx} className="flex gap-2">
                            <Input
                              placeholder="KEY"
                              value={env.key}
                              onChange={(e) => updateEnvVar(idx, 'key', e.target.value)}
                              className="w-1/3"
                            />
                            <Input
                              placeholder="value"
                              value={env.value}
                              onChange={(e) => updateEnvVar(idx, 'value', e.target.value)}
                              className="flex-1"
                            />
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removeEnvVar(idx)}
                            >
                              <Trash2 className="h-4 w-4 text-red-400" />
                            </Button>
                          </div>
                        ))}
                        {customEnvVars.length === 0 && (
                          <p className="text-sm text-foreground-muted text-center py-4">
                            No custom environment variables
                          </p>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Prompt Editor */}
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="h-5 w-5 text-neon-green" />
                      Prompt Template
                      {promptEditorDirty && (
                        <Badge variant="warning" size="sm">
                          Unsaved
                        </Badge>
                      )}
                    </CardTitle>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowHistoryDialog(true)}
                      >
                        <History className="h-4 w-4 mr-2" />
                        History
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => resetPromptMutation.mutate()}
                        loading={resetPromptMutation.isPending}
                      >
                        <RotateCcw className="h-4 w-4 mr-2" />
                        Default
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Active Prompt Info */}
                    {activePrompt && (
                      <div className="text-xs text-foreground-muted">
                        Active: {activePrompt.path}
                      </div>
                    )}

                    {/* Prompt Editor */}
                    <Textarea
                      value={promptEditorContent}
                      onChange={(e) => {
                        setPromptEditorContent(e.target.value)
                        setPromptEditorDirty(true)
                      }}
                      className="min-h-[400px] font-mono text-sm"
                      placeholder="Enter prompt template..."
                    />

                    {/* Version Note */}
                    <div className="space-y-2">
                      <Label>Version Note (optional)</Label>
                      <Input
                        placeholder="Description of changes..."
                        value={promptNote}
                        onChange={(e) => setPromptNote(e.target.value)}
                      />
                    </div>

                    {/* Save Button */}
                    <Button
                      onClick={() => savePromptMutation.mutate()}
                      loading={savePromptMutation.isPending}
                      disabled={!promptEditorDirty}
                      className="w-full gap-2"
                    >
                      <Save className="h-4 w-4" />
                      Save New Version
                    </Button>
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>

      {/* Prompt History Dialog */}
      <Dialog open={showHistoryDialog} onOpenChange={setShowHistoryDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Prompt Version History</DialogTitle>
            <DialogDescription>
              View and revert to previous prompt versions
            </DialogDescription>
          </DialogHeader>
          <ScrollArea className="h-[400px]">
            <div className="space-y-3 pr-4">
              {promptHistory.map((version, idx) => (
                <div
                  key={version.path}
                  className={cn(
                    'p-4 rounded-lg border cursor-pointer transition-all duration-300',
                    selectedVersion?.path === version.path
                      ? 'border-neon-cyan bg-neon-cyan/10'
                      : 'border-border bg-background-secondary hover:border-neon-cyan/50'
                  )}
                  onClick={() => setSelectedVersion(version)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-mono text-sm text-foreground">
                        {version.path.split('/').pop()}
                      </p>
                      {version.note && (
                        <p className="text-sm text-foreground-muted mt-1">
                          {version.note}
                        </p>
                      )}
                    </div>
                    <span className="text-xs text-foreground-subtle">
                      {formatDateTime(version.timestamp)}
                    </span>
                  </div>
                </div>
              ))}
              {promptHistory.length === 0 && (
                <div className="py-8 text-center text-foreground-muted">
                  No version history
                </div>
              )}
            </div>
          </ScrollArea>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowHistoryDialog(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={() =>
                selectedVersion && revertPromptMutation.mutate(selectedVersion.path)
              }
              loading={revertPromptMutation.isPending}
              disabled={!selectedVersion}
            >
              Revert to Selected
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
