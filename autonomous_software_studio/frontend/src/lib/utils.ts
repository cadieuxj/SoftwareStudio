import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { formatDistanceToNow, format } from 'date-fns'
import type { SessionStatus, SessionPhase, AgentRole } from '@/types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatRelativeTime(dateString: string): string {
  try {
    return formatDistanceToNow(new Date(dateString), { addSuffix: true })
  } catch {
    return 'unknown'
  }
}

export function formatDateTime(dateString: string): string {
  try {
    return format(new Date(dateString), 'MMM d, yyyy HH:mm:ss')
  } catch {
    return dateString
  }
}

export function getStatusColor(status: SessionStatus): string {
  const map: Record<SessionStatus, string> = {
    pending: 'text-foreground-muted',
    running: 'text-neon-cyan',
    awaiting_approval: 'text-neon-orange',
    completed: 'text-neon-green',
    failed: 'text-red-400',
    expired: 'text-foreground-subtle',
  }
  return map[status] ?? 'text-foreground-muted'
}

export function getStatusLabel(status: SessionStatus): string {
  const map: Record<SessionStatus, string> = {
    pending: 'Pending',
    running: 'Running',
    awaiting_approval: 'Awaiting Review',
    completed: 'Completed',
    failed: 'Failed',
    expired: 'Expired',
  }
  return map[status] ?? status
}

export function getPhaseLabel(phase: SessionPhase): string {
  const map: Record<SessionPhase, string> = {
    pm: 'Product Manager',
    arch: 'Architect',
    human_gate: 'Human Review',
    engineer: 'Engineer',
    qa: 'QA',
    complete: 'Complete',
    failed: 'Failed',
  }
  return map[phase] ?? phase
}

export function getAgentLabel(role: AgentRole): string {
  const map: Record<AgentRole, string> = {
    pm: 'Product Manager',
    architect: 'Architect',
    engineer: 'Engineer',
    qa: 'QA',
  }
  return map[role] ?? role
}

export function getAgentColor(role: AgentRole): string {
  const map: Record<AgentRole, string> = {
    pm: 'text-neon-cyan',
    architect: 'text-neon-magenta',
    engineer: 'text-neon-green',
    qa: 'text-neon-orange',
  }
  return map[role] ?? 'text-foreground'
}

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str
  return str.slice(0, length) + '...'
}

export function downloadAsFile(content: string, filename: string, mime = 'text/plain'): void {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
