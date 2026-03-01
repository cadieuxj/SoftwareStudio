'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  PlayCircle,
  FileText,
  CheckCircle2,
  ScrollText,
  Github,
  FolderKanban,
  Bot,
  ChevronLeft,
  Terminal,
  Zap,
  Users,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useUIStore } from '@/store'

const navItems = [
  { label: 'Dashboard',  href: '/',          icon: LayoutDashboard },
  { label: 'Sessions',   href: '/sessions',  icon: PlayCircle      },
  { label: 'Projects',   href: '/projects',  icon: FolderKanban    },
  { label: 'Team',       href: '/team',      icon: Users           },
  { label: 'Artifacts',  href: '/artifacts', icon: FileText        },
  { label: 'Approvals',  href: '/approvals', icon: CheckCircle2    },
  { label: 'Logs',       href: '/logs',      icon: ScrollText      },
  { label: 'GitHub',     href: '/github',    icon: Github          },
  { label: 'Agents',     href: '/agents',    icon: Bot             },
  { label: 'Sandbox',    href: '/sandbox',   icon: Terminal        },
]

export function Sidebar() {
  const pathname = usePathname()
  const { sidebarOpen, toggleSidebar } = useUIStore()

  return (
    <motion.aside
      initial={false}
      animate={{ width: sidebarOpen ? 220 : 60 }}
      transition={{ duration: 0.2, ease: 'easeInOut' }}
      className="fixed left-0 top-0 z-40 h-screen flex flex-col bg-background-secondary border-r border-white/[0.06] overflow-hidden"
    >
      {/* Logo */}
      <div className="flex h-14 items-center gap-3 px-3.5 border-b border-white/[0.06] flex-shrink-0">
        <Link href="/" className="flex items-center gap-3 min-w-0">
          <div className="flex-shrink-0 h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
            <Zap className="h-4 w-4 text-indigo-400" />
          </div>
          <AnimatePresence mode="wait">
            {sidebarOpen && (
              <motion.div
                key="logo-text"
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -6 }}
                transition={{ duration: 0.15 }}
                className="min-w-0"
              >
                <p className="font-semibold text-sm text-foreground leading-tight truncate">
                  Sovereign AI
                </p>
                <p className="text-[11px] text-foreground-subtle leading-tight">
                  Dev Studio
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-2 px-2">
        <ul className="space-y-0.5">
          {navItems.map((item) => {
            const isActive = pathname === item.href
            const Icon = item.icon

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    'relative flex items-center gap-3 h-9 px-2.5 rounded-md',
                    'text-sm transition-colors duration-150 group',
                    isActive
                      ? 'bg-indigo-500/10 text-indigo-300'
                      : 'text-foreground-muted hover:text-foreground hover:bg-white/[0.05]'
                  )}
                >
                  {/* Active left bar */}
                  {isActive && (
                    <motion.span
                      layoutId="navIndicator"
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-indigo-400 rounded-r-full"
                      transition={{ duration: 0.2 }}
                    />
                  )}

                  <Icon className="h-4 w-4 flex-shrink-0" />

                  <AnimatePresence mode="wait">
                    {sidebarOpen && (
                      <motion.span
                        key="nav-label"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.12 }}
                        className="font-medium truncate"
                      >
                        {item.label}
                      </motion.span>
                    )}
                  </AnimatePresence>
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Collapse toggle */}
      <div className="border-t border-white/[0.06] p-3 flex-shrink-0">
        <button
          onClick={toggleSidebar}
          className="flex items-center justify-center h-8 w-8 rounded-md text-foreground-subtle hover:text-foreground hover:bg-white/[0.06] transition-colors"
          aria-label="Toggle sidebar"
        >
          <ChevronLeft
            className={cn(
              'h-4 w-4 transition-transform duration-200',
              !sidebarOpen && 'rotate-180'
            )}
          />
        </button>
      </div>
    </motion.aside>
  )
}
