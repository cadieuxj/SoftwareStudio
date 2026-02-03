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
  Settings,
  Bot,
  ChevronLeft,
  Sparkles,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useUIStore } from '@/store'
import { Button } from '@/components/ui'

const navItems = [
  {
    label: 'Dashboard',
    href: '/',
    icon: LayoutDashboard,
    description: 'Overview & Metrics',
  },
  {
    label: 'Sessions',
    href: '/sessions',
    icon: PlayCircle,
    description: 'Manage Sessions',
  },
  {
    label: 'Artifacts',
    href: '/artifacts',
    icon: FileText,
    description: 'Review Artifacts',
  },
  {
    label: 'Approvals',
    href: '/approvals',
    icon: CheckCircle2,
    description: 'Pending Reviews',
  },
  {
    label: 'Logs',
    href: '/logs',
    icon: ScrollText,
    description: 'Live Logs',
  },
  {
    label: 'GitHub',
    href: '/github',
    icon: Github,
    description: 'Repository Integration',
  },
  {
    label: 'Projects',
    href: '/projects',
    icon: Settings,
    description: 'Project Settings',
  },
  {
    label: 'Agents',
    href: '/agents',
    icon: Bot,
    description: 'Agent Configuration',
  },
]

export function Sidebar() {
  const pathname = usePathname()
  const { sidebarOpen, toggleSidebar } = useUIStore()

  return (
    <motion.aside
      initial={false}
      animate={{ width: sidebarOpen ? 280 : 80 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className={cn(
        'fixed left-0 top-0 z-40 h-screen',
        'bg-background-secondary/80 backdrop-blur-xl',
        'border-r border-border',
        'flex flex-col'
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-border">
        <Link href="/" className="flex items-center gap-3">
          <div className="relative">
            <Sparkles className="h-8 w-8 text-neon-cyan" />
            <div className="absolute inset-0 blur-lg bg-neon-cyan/30" />
          </div>
          <AnimatePresence mode="wait">
            {sidebarOpen && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
              >
                <h1 className="font-display text-lg font-bold tracking-wider text-foreground">
                  <span className="text-neon-cyan">AUTO</span>
                  <span className="text-neon-magenta">STUDIO</span>
                </h1>
                <p className="text-[10px] uppercase tracking-[0.2em] text-foreground-subtle">
                  Software Factory
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href
            const Icon = item.icon

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-3',
                    'transition-all duration-300',
                    'group relative overflow-hidden',
                    isActive
                      ? 'bg-gradient-to-r from-neon-cyan/20 to-neon-magenta/10 text-neon-cyan border border-neon-cyan/30'
                      : 'text-foreground-muted hover:text-foreground hover:bg-background-tertiary'
                  )}
                >
                  {/* Glow effect on hover */}
                  <div
                    className={cn(
                      'absolute inset-0 opacity-0 group-hover:opacity-100',
                      'bg-gradient-to-r from-neon-cyan/5 to-transparent',
                      'transition-opacity duration-300'
                    )}
                  />

                  <Icon
                    className={cn(
                      'h-5 w-5 shrink-0 relative z-10',
                      'transition-colors duration-300',
                      isActive && 'text-glow-cyan'
                    )}
                  />

                  <AnimatePresence mode="wait">
                    {sidebarOpen && (
                      <motion.div
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -10 }}
                        transition={{ duration: 0.2 }}
                        className="relative z-10 flex flex-col"
                      >
                        <span className="font-display text-sm font-medium">
                          {item.label}
                        </span>
                        <span className="text-[10px] text-foreground-subtle">
                          {item.description}
                        </span>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Active indicator */}
                  {isActive && (
                    <motion.div
                      layoutId="activeIndicator"
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-neon-cyan rounded-r-full"
                      transition={{ duration: 0.3 }}
                    />
                  )}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Toggle Button */}
      <div className="border-t border-border p-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className={cn(
            'w-full justify-center',
            sidebarOpen && 'justify-end'
          )}
        >
          <ChevronLeft
            className={cn(
              'h-5 w-5 transition-transform duration-300',
              !sidebarOpen && 'rotate-180'
            )}
          />
        </Button>
      </div>

      {/* Version Info */}
      <AnimatePresence mode="wait">
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="px-4 pb-4 text-center"
          >
            <p className="text-[10px] text-foreground-subtle">
              v1.0.0 | 2055+ Edition
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.aside>
  )
}
