'use client'

import { useState, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Play,
  Square,
  Plus,
  Terminal,
  Code2,
  Loader2,
  CheckCircle2,
  XCircle,
  Trash2,
  Copy,
  Download,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn, copyToClipboard, downloadAsFile } from '@/lib/utils'
import toast from 'react-hot-toast'
import type { SupportedLanguage } from '@/lib/e2b'
import { LANGUAGE_TEMPLATES } from '@/lib/e2b'

// ---------------------------------------------------------------------------

interface OutputBlock {
  id: string
  code: string
  stdout: string
  stderr: string
  error?: string
  durationMs?: number
  results: { type: string; data: unknown }[]
  timestamp: Date
}

interface ActiveSandbox {
  sandboxId: string        // DB record ID
  e2bSandboxId: string
  language: SupportedLanguage
  status: 'running' | 'stopped' | 'error'
}

const LANGUAGES: { value: SupportedLanguage; label: string }[] = [
  { value: 'python', label: 'Python 3' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'bash', label: 'Bash' },
]

// ---------------------------------------------------------------------------

export default function SandboxPage() {
  const [sandbox, setSandbox] = useState<ActiveSandbox | null>(null)
  const [language, setLanguage] = useState<SupportedLanguage>('python')
  const [code, setCode] = useState(LANGUAGE_TEMPLATES['python'])
  const [outputs, setOutputs] = useState<OutputBlock[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const outputEndRef = useRef<HTMLDivElement>(null)

  const handleLanguageChange = useCallback((lang: SupportedLanguage) => {
    setLanguage(lang)
    setCode(LANGUAGE_TEMPLATES[lang])
  }, [])

  const createSandbox = async () => {
    setIsCreating(true)
    try {
      const res = await fetch('/api/sandbox', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language }),
      })
      if (!res.ok) throw new Error((await res.json()).error ?? 'Failed to create sandbox')
      const data = await res.json()
      setSandbox({ sandboxId: data.sandboxId, e2bSandboxId: data.e2bSandboxId, language, status: 'running' })
      toast.success('Sandbox started')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create sandbox')
    } finally {
      setIsCreating(false)
    }
  }

  const runCode = async () => {
    if (!sandbox || !code.trim()) return
    setIsRunning(true)
    const block: OutputBlock = {
      id: crypto.randomUUID(),
      code,
      stdout: '',
      stderr: '',
      results: [],
      timestamp: new Date(),
    }

    try {
      const res = await fetch(`/api/sandbox/${sandbox.sandboxId}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, language }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error ?? 'Execution failed')
      block.stdout = data.stdout ?? ''
      block.stderr = data.stderr ?? ''
      block.error = data.error
      block.results = data.results ?? []
      block.durationMs = data.durationMs
    } catch (err) {
      block.error = err instanceof Error ? err.message : 'Unknown error'
    } finally {
      setIsRunning(false)
      setOutputs((prev) => [...prev, block])
      setTimeout(() => outputEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    }
  }

  const clearOutputs = () => setOutputs([])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Shift+Enter to run
    if (e.key === 'Enter' && e.shiftKey) {
      e.preventDefault()
      runCode()
      return
    }
    // Tab → indent
    if (e.key === 'Tab') {
      e.preventDefault()
      const ta = textareaRef.current!
      const { selectionStart: s, selectionEnd: end } = ta
      const newCode = code.slice(0, s) + '  ' + code.slice(end)
      setCode(newCode)
      requestAnimationFrame(() => ta.setSelectionRange(s + 2, s + 2))
    }
  }

  return (
    <div className="flex flex-col gap-6 h-[calc(100vh-5rem)]">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold font-display text-foreground tracking-wide">
            Code Sandbox
          </h1>
          <p className="text-foreground-muted text-sm mt-1">
            Isolated E2B execution environments for your AI sessions
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Select
            value={language}
            onValueChange={(v) => handleLanguageChange(v as SupportedLanguage)}
            disabled={!!sandbox}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LANGUAGES.map((l) => (
                <SelectItem key={l.value} value={l.value}>
                  {l.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {!sandbox ? (
            <Button onClick={createSandbox} disabled={isCreating}>
              {isCreating ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Plus className="w-4 h-4 mr-2" />
              )}
              {isCreating ? 'Starting…' : 'New Sandbox'}
            </Button>
          ) : (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neon-green/10 border border-neon-green/30">
                <span className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
                <span className="text-neon-green text-xs font-mono">
                  {sandbox.e2bSandboxId.slice(0, 12)}…
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSandbox(null)
                  toast.success('Sandbox disconnected')
                }}
              >
                <Square className="w-4 h-4 mr-1" />
                Disconnect
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Main split */}
      <div className="grid grid-cols-2 gap-4 flex-1 min-h-0">
        {/* Editor pane */}
        <Card className="flex flex-col min-h-0">
          <CardHeader className="flex-shrink-0 flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Code2 className="w-4 h-4 text-neon-cyan" />
              Editor
              {sandbox && (
                <Badge variant="secondary" className="ml-2 text-xs">
                  {language}
                </Badge>
              )}
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => copyToClipboard(code).then(() => toast.success('Copied'))}
              >
                <Copy className="w-3.5 h-3.5" />
              </Button>
              <Button
                size="sm"
                onClick={runCode}
                disabled={!sandbox || isRunning}
                className="bg-neon-green/20 hover:bg-neon-green/30 border border-neon-green/40 text-neon-green"
              >
                {isRunning ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-1.5" />
                ) : (
                  <Play className="w-4 h-4 mr-1.5" />
                )}
                {isRunning ? 'Running…' : 'Run'}
                <kbd className="ml-2 text-[10px] opacity-60">⇧↵</kbd>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex-1 min-h-0 p-0">
            <textarea
              ref={textareaRef}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onKeyDown={handleKeyDown}
              className={cn(
                'w-full h-full resize-none bg-transparent p-4',
                'font-mono text-sm text-foreground',
                'focus:outline-none focus:ring-0 border-0',
                'placeholder:text-foreground-subtle'
              )}
              spellCheck={false}
              placeholder={sandbox ? 'Write code here… Shift+Enter to run' : 'Start a sandbox to begin coding'}
            />
          </CardContent>
        </Card>

        {/* Output pane */}
        <Card className="flex flex-col min-h-0">
          <CardHeader className="flex-shrink-0 flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Terminal className="w-4 h-4 text-neon-magenta" />
              Output
              {outputs.length > 0 && (
                <Badge variant="secondary" className="ml-1 text-xs">
                  {outputs.length}
                </Badge>
              )}
            </CardTitle>
            {outputs.length > 0 && (
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    downloadAsFile(
                      outputs.map((o) => `# ${o.timestamp.toISOString()}\n${o.stdout}${o.stderr}`).join('\n\n---\n\n'),
                      'sandbox-output.txt'
                    )
                  }
                >
                  <Download className="w-3.5 h-3.5" />
                </Button>
                <Button variant="ghost" size="sm" onClick={clearOutputs}>
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            )}
          </CardHeader>
          <CardContent className="flex-1 min-h-0 p-0">
            <ScrollArea className="h-full">
              <div className="p-4 space-y-4">
                <AnimatePresence initial={false}>
                  {outputs.length === 0 && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex flex-col items-center justify-center h-40 gap-2 text-foreground-subtle"
                    >
                      <Terminal className="w-8 h-8 opacity-30" />
                      <p className="text-sm">No output yet</p>
                    </motion.div>
                  )}

                  {outputs.map((block) => (
                    <motion.div
                      key={block.id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="rounded-lg border border-border overflow-hidden"
                    >
                      {/* Block header */}
                      <div className="flex items-center justify-between px-3 py-1.5 bg-background-secondary border-b border-border">
                        <span className="text-xs text-foreground-muted font-mono">
                          {block.timestamp.toLocaleTimeString()}
                        </span>
                        <div className="flex items-center gap-2">
                          {block.durationMs !== undefined && (
                            <span className="text-xs text-foreground-subtle">
                              {block.durationMs}ms
                            </span>
                          )}
                          {block.error ? (
                            <XCircle className="w-3.5 h-3.5 text-red-400" />
                          ) : (
                            <CheckCircle2 className="w-3.5 h-3.5 text-neon-green" />
                          )}
                        </div>
                      </div>

                      {/* stdout */}
                      {block.stdout && (
                        <pre className="p-3 text-xs font-mono text-neon-green bg-neon-green/5 whitespace-pre-wrap break-words">
                          {block.stdout}
                        </pre>
                      )}

                      {/* stderr */}
                      {block.stderr && (
                        <pre className="p-3 text-xs font-mono text-neon-orange bg-neon-orange/5 whitespace-pre-wrap break-words border-t border-border">
                          {block.stderr}
                        </pre>
                      )}

                      {/* error */}
                      {block.error && (
                        <pre className="p-3 text-xs font-mono text-red-400 bg-red-500/5 whitespace-pre-wrap break-words border-t border-border">
                          {block.error}
                        </pre>
                      )}

                      {/* rich results (images, dataframes, etc.) */}
                      {block.results
                        .filter((r) => r.type === 'image/png' || r.type === 'text/plain')
                        .map((r, i) => (
                          <div key={i} className="p-3 border-t border-border">
                            {r.type === 'image/png' ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img
                                src={`data:image/png;base64,${r.data}`}
                                alt="execution result"
                                className="max-w-full rounded"
                              />
                            ) : (
                              <pre className="text-xs font-mono text-foreground-muted whitespace-pre-wrap">
                                {String(r.data)}
                              </pre>
                            )}
                          </div>
                        ))}
                    </motion.div>
                  ))}
                </AnimatePresence>
                <div ref={outputEndRef} />
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
