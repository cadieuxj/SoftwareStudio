import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Session, SessionStatus, AgentRole } from '@/types'

// UI Store
interface UIState {
  sidebarOpen: boolean
  theme: 'dark' | 'light'
  logsAutoRefresh: boolean
  logsRefreshInterval: number
  selectedSessionId: string | null
  selectedProjectName: string | null
  sessionFilter: SessionStatus | 'all'
  kanbanViewEnabled: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  setTheme: (theme: 'dark' | 'light') => void
  setLogsAutoRefresh: (enabled: boolean) => void
  setLogsRefreshInterval: (interval: number) => void
  setSelectedSessionId: (id: string | null) => void
  setSelectedProjectName: (name: string | null) => void
  setSessionFilter: (filter: SessionStatus | 'all') => void
  setKanbanViewEnabled: (enabled: boolean) => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: 'dark',
      logsAutoRefresh: true,
      logsRefreshInterval: 5000,
      selectedSessionId: null,
      selectedProjectName: null,
      sessionFilter: 'all',
      kanbanViewEnabled: true,
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setTheme: (theme) => set({ theme }),
      setLogsAutoRefresh: (enabled) => set({ logsAutoRefresh: enabled }),
      setLogsRefreshInterval: (interval) => set({ logsRefreshInterval: interval }),
      setSelectedSessionId: (id) => set({ selectedSessionId: id }),
      setSelectedProjectName: (name) => set({ selectedProjectName: name }),
      setSessionFilter: (filter) => set({ sessionFilter: filter }),
      setKanbanViewEnabled: (enabled) => set({ kanbanViewEnabled: enabled }),
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        theme: state.theme,
        logsAutoRefresh: state.logsAutoRefresh,
        logsRefreshInterval: state.logsRefreshInterval,
        kanbanViewEnabled: state.kanbanViewEnabled,
        sidebarOpen: state.sidebarOpen,
      }),
    }
  )
)

// Sessions Store
interface SessionsState {
  sessions: Session[]
  isLoading: boolean
  error: string | null
  setSessions: (sessions: Session[]) => void
  addSession: (session: Session) => void
  updateSession: (sessionId: string, updates: Partial<Session>) => void
  removeSession: (sessionId: string) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useSessionsStore = create<SessionsState>((set) => ({
  sessions: [],
  isLoading: false,
  error: null,
  setSessions: (sessions) => set({ sessions, error: null }),
  addSession: (session) =>
    set((state) => ({ sessions: [session, ...state.sessions] })),
  updateSession: (sessionId, updates) =>
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.session_id === sessionId ? { ...s, ...updates } : s
      ),
    })),
  removeSession: (sessionId) =>
    set((state) => ({
      sessions: state.sessions.filter((s) => s.session_id !== sessionId),
    })),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
}))

// Agent Settings Store
interface AgentSettingsState {
  selectedAgent: AgentRole
  promptEditorContent: string
  promptEditorDirty: boolean
  setSelectedAgent: (agent: AgentRole) => void
  setPromptEditorContent: (content: string) => void
  setPromptEditorDirty: (dirty: boolean) => void
}

export const useAgentSettingsStore = create<AgentSettingsState>((set) => ({
  selectedAgent: 'pm',
  promptEditorContent: '',
  promptEditorDirty: false,
  setSelectedAgent: (agent) => set({ selectedAgent: agent }),
  setPromptEditorContent: (content) => set({ promptEditorContent: content, promptEditorDirty: true }),
  setPromptEditorDirty: (dirty) => set({ promptEditorDirty: dirty }),
}))

// GitHub Store
interface GitHubState {
  selectedOrg: string | null
  selectedRepo: { owner: string; name: string } | null
  isAuthenticated: boolean
  username: string | null
  setSelectedOrg: (org: string | null) => void
  setSelectedRepo: (repo: { owner: string; name: string } | null) => void
  setAuthenticated: (authenticated: boolean, username?: string) => void
}

export const useGitHubStore = create<GitHubState>()(
  persist(
    (set) => ({
      selectedOrg: null,
      selectedRepo: null,
      isAuthenticated: false,
      username: null,
      setSelectedOrg: (org) => set({ selectedOrg: org }),
      setSelectedRepo: (repo) => set({ selectedRepo: repo }),
      setAuthenticated: (authenticated, username) =>
        set({ isAuthenticated: authenticated, username: username || null }),
    }),
    {
      name: 'github-storage',
      partialize: (state) => ({
        selectedOrg: state.selectedOrg,
      }),
    }
  )
)

// Create Session Modal Store
interface CreateSessionModalState {
  isOpen: boolean
  prefillMission: string
  prefillProjectName: string
  open: (mission?: string, projectName?: string) => void
  close: () => void
}

export const useCreateSessionModal = create<CreateSessionModalState>((set) => ({
  isOpen: false,
  prefillMission: '',
  prefillProjectName: '',
  open: (mission = '', projectName = '') =>
    set({ isOpen: true, prefillMission: mission, prefillProjectName: projectName }),
  close: () => set({ isOpen: false, prefillMission: '', prefillProjectName: '' }),
}))

// Notification Store
interface Notification {
  id: string
  type: 'success' | 'error' | 'info' | 'warning'
  message: string
  duration?: number
}

interface NotificationState {
  notifications: Notification[]
  addNotification: (notification: Omit<Notification, 'id'>) => void
  removeNotification: (id: string) => void
  clearAll: () => void
}

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  addNotification: (notification) =>
    set((state) => ({
      notifications: [
        ...state.notifications,
        { ...notification, id: Math.random().toString(36).slice(2) },
      ],
    })),
  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),
  clearAll: () => set({ notifications: [] }),
}))
