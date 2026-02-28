/**
 * Client-safe E2B constants — no Node.js imports.
 * Import this in client components instead of lib/e2b.ts.
 */

export type SupportedLanguage = 'python' | 'javascript' | 'typescript' | 'bash'

export const LANGUAGE_TEMPLATES: Record<SupportedLanguage, string> = {
  python: '# Python 3\nprint("Hello from Sovereign AI sandbox!")',
  javascript: '// Node.js\nconsole.log("Hello from Sovereign AI sandbox!")',
  typescript:
    '// TypeScript\nconst msg: string = "Hello from Sovereign AI sandbox!"\nconsole.log(msg)',
  bash: '#!/bin/bash\necho "Hello from Sovereign AI sandbox!"',
}
