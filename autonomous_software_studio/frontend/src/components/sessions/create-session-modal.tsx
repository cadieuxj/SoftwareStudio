'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Rocket, Sparkles } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { sessionsApi, queryKeys } from '@/lib/api'
import { useCreateSessionModal } from '@/store'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  Button,
  Input,
  Textarea,
  Label,
} from '@/components/ui'

export function CreateSessionModal() {
  const { isOpen, prefillMission, prefillProjectName, close } = useCreateSessionModal()
  const queryClient = useQueryClient()

  const [mission, setMission] = useState(prefillMission)
  const [projectName, setProjectName] = useState(prefillProjectName)

  // Reset form when modal opens with prefill
  useState(() => {
    setMission(prefillMission)
    setProjectName(prefillProjectName)
  })

  const createMutation = useMutation({
    mutationFn: sessionsApi.create,
    onSuccess: (session) => {
      toast.success(`Session "${session.project_name}" created!`)
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions })
      queryClient.invalidateQueries({ queryKey: queryKeys.metrics })
      handleClose()
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Failed to create session')
    },
  })

  const handleClose = () => {
    setMission('')
    setProjectName('')
    close()
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!mission.trim()) {
      toast.error('Mission is required')
      return
    }
    createMutation.mutate({
      mission: mission.trim(),
      project_name: projectName.trim() || undefined,
    })
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <Sparkles className="h-6 w-6 text-neon-cyan" />
            <span>Create New Session</span>
          </DialogTitle>
          <DialogDescription>
            Describe your mission and let the AI agents build it for you.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6 py-4">
          {/* Mission */}
          <div className="space-y-2">
            <Label htmlFor="mission" className="text-foreground">
              Mission <span className="text-red-400">*</span>
            </Label>
            <Textarea
              id="mission"
              placeholder="Describe what you want to build... e.g., 'Build a REST API for a todo application with user authentication, CRUD operations for tasks, and PostgreSQL storage.'"
              value={mission}
              onChange={(e) => setMission(e.target.value)}
              className="min-h-[150px] resize-y"
            />
            <p className="text-xs text-foreground-subtle">
              Be specific about features, technologies, and requirements.
            </p>
          </div>

          {/* Project Name */}
          <div className="space-y-2">
            <Label htmlFor="projectName" className="text-foreground">
              Project Name <span className="text-foreground-subtle">(optional)</span>
            </Label>
            <Input
              id="projectName"
              placeholder="my-awesome-project"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
            />
            <p className="text-xs text-foreground-subtle">
              Leave empty to auto-generate from mission.
            </p>
          </div>

          {/* Info Box */}
          <div className="rounded-lg border border-neon-cyan/30 bg-neon-cyan/5 p-4">
            <h4 className="font-display text-sm font-semibold text-neon-cyan mb-2">
              What happens next?
            </h4>
            <ol className="text-sm text-foreground-muted space-y-1 list-decimal list-inside">
              <li>PM Agent creates a detailed Product Requirements Document</li>
              <li>Architect Agent designs the technical specification</li>
              <li>You review and approve the architecture</li>
              <li>Engineer Agent implements the code</li>
              <li>QA Agent tests and validates the implementation</li>
            </ol>
          </div>
        </form>

        <DialogFooter className="gap-3">
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            loading={createMutation.isPending}
            className="gap-2"
          >
            <Rocket className="h-4 w-4" />
            Launch Session
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
