import { SignUp } from '@clerk/nextjs'

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background cyber-grid">
      <div className="fixed inset-0 bg-gradient-to-br from-neon-cyan/5 via-transparent to-neon-magenta/5 pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center gap-8">
        <div className="flex flex-col items-center gap-2">
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold tracking-widest font-display text-neon-cyan text-glow-cyan">
              SOVEREIGN
            </span>
            <span className="text-2xl font-bold tracking-widest font-display text-neon-magenta">
              AI
            </span>
          </div>
          <p className="text-foreground-muted text-sm tracking-wider">
            Create your organization
          </p>
        </div>

        <SignUp
          appearance={{
            variables: {
              colorBackground: '#0f0f1a',
              colorText: '#e8e8f0',
              colorPrimary: '#00ffff',
              colorDanger: '#ff4444',
              colorInputBackground: '#1a1a2e',
              colorInputText: '#e8e8f0',
              borderRadius: '0.75rem',
              fontFamily: 'Rajdhani, sans-serif',
            },
            elements: {
              card: 'bg-background-secondary border border-border shadow-2xl',
              headerTitle: 'text-foreground font-display tracking-wide',
              formButtonPrimary:
                'bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan',
              footerActionLink: 'text-neon-cyan hover:text-neon-cyan/80',
            },
          }}
        />
      </div>
    </div>
  )
}
