'use client'

import { useQuery } from '@tanstack/react-query'
import { Users, Activity, Calendar, Crown, Shield, User } from 'lucide-react'
import { teamApi, queryKeys } from '@/lib/api'
import { formatRelativeTime, formatDateTime } from '@/lib/utils'
import { Card, CardContent, Badge } from '@/components/ui'
import type { TeamMember } from '@/types'

function getRoleIcon(role: string) {
  if (role.includes('admin') || role === 'org:admin') return Crown
  if (role.includes('member') || role === 'org:member') return User
  return Shield
}

function getRoleBadgeVariant(role: string): 'default' | 'secondary' | 'running' {
  if (role.includes('admin')) return 'running'
  if (role.includes('member')) return 'secondary'
  return 'default'
}

function getRoleLabel(role: string): string {
  const map: Record<string, string> = {
    'org:admin': 'Admin',
    'org:member': 'Member',
    admin: 'Admin',
    member: 'Member',
    basic_member: 'Member',
  }
  return map[role] ?? role
}

function MemberCard({ member }: { member: TeamMember }) {
  const RoleIcon = getRoleIcon(member.role)
  const initials = [member.firstName, member.lastName]
    .filter(Boolean)
    .map((n) => n![0].toUpperCase())
    .join('') || (member.email?.[0]?.toUpperCase() ?? '?')

  return (
    <Card className="hover:border-white/[0.12] transition-colors duration-150">
      <CardContent className="pt-5">
        <div className="flex items-start gap-4">
          {/* Avatar */}
          <div className="flex-shrink-0">
            {member.avatarUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={member.avatarUrl}
                alt={initials}
                className="h-11 w-11 rounded-full object-cover ring-2 ring-white/10"
              />
            ) : (
              <div className="h-11 w-11 rounded-full bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-300 font-semibold text-sm">
                {initials}
              </div>
            )}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-foreground text-sm truncate">
                {[member.firstName, member.lastName].filter(Boolean).join(' ') || 'Unknown'}
              </span>
              <Badge variant={getRoleBadgeVariant(member.role)} className="text-[10px]">
                <RoleIcon className="h-3 w-3 mr-1" />
                {getRoleLabel(member.role)}
              </Badge>
            </div>
            {member.email && (
              <p className="text-xs text-foreground-muted mt-0.5 truncate">{member.email}</p>
            )}

            <div className="mt-3 flex items-center gap-4 text-xs text-foreground-subtle">
              {/* Session count */}
              <div className="flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5 text-indigo-400" />
                <span>
                  <span className="text-foreground font-medium">{member.sessionCount}</span>
                  {' '}session{member.sessionCount !== 1 ? 's' : ''}
                </span>
              </div>

              {/* Last active */}
              {member.lastActive && (
                <div className="flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5" />
                  <span>Active {formatRelativeTime(member.lastActive)}</span>
                </div>
              )}

              {/* Joined */}
              {member.joinedAt && (
                <div className="flex items-center gap-1.5 hidden sm:flex">
                  <span>Joined {formatDateTime(member.joinedAt).split(' ')[0]}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function TeamPage() {
  const { data: members, isLoading, isError } = useQuery({
    queryKey: queryKeys.team,
    queryFn: teamApi.list,
    staleTime: 60_000,
  })

  const admins = members?.filter((m) => m.role.includes('admin')) ?? []
  const regularMembers = members?.filter((m) => !m.role.includes('admin')) ?? []

  const totalSessions = members?.reduce((sum, m) => sum + m.sessionCount, 0) ?? 0
  const activeMembers = members?.filter((m) => m.sessionCount > 0).length ?? 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Team</h1>
        <p className="text-sm text-foreground-muted mt-1">
          Manage your organization members and their activity
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-foreground-muted">Members</p>
            <p className="text-2xl font-semibold text-foreground mt-1">
              {isLoading ? '—' : (members?.length ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-foreground-muted">Admins</p>
            <p className="text-2xl font-semibold text-indigo-400 mt-1">
              {isLoading ? '—' : admins.length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-foreground-muted">Active builders</p>
            <p className="text-2xl font-semibold text-emerald-400 mt-1">
              {isLoading ? '—' : activeMembers}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-foreground-muted">Total sessions</p>
            <p className="text-2xl font-semibold text-foreground mt-1">
              {isLoading ? '—' : totalSessions}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Member list */}
      {isError && (
        <Card>
          <CardContent className="pt-6 pb-6 text-center text-foreground-muted text-sm">
            Could not load team members. Make sure your organization is set up correctly.
          </CardContent>
        </Card>
      )}

      {isLoading && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 rounded-lg bg-background-secondary/60 animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && !isError && (
        <div className="space-y-6">
          {admins.length > 0 && (
            <div>
              <h2 className="text-xs font-medium text-foreground-subtle uppercase tracking-wider mb-3 flex items-center gap-2">
                <Crown className="h-3.5 w-3.5 text-amber-400" />
                Administrators
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {admins.map((m) => (
                  <MemberCard key={m.id} member={m} />
                ))}
              </div>
            </div>
          )}

          {regularMembers.length > 0 && (
            <div>
              <h2 className="text-xs font-medium text-foreground-subtle uppercase tracking-wider mb-3 flex items-center gap-2">
                <Users className="h-3.5 w-3.5" />
                Members
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {regularMembers.map((m) => (
                  <MemberCard key={m.id} member={m} />
                ))}
              </div>
            </div>
          )}

          {members?.length === 0 && (
            <Card>
              <CardContent className="pt-12 pb-12 text-center">
                <Users className="h-10 w-10 text-foreground-subtle mx-auto mb-3" />
                <p className="text-foreground-muted text-sm">No team members found</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
