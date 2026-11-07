import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Privacy Policy — Blender Skills',
}

export default function PrivacyPage() {
  return (
    <div className="max-w-2xl mx-auto px-6 py-16 space-y-8 text-sm text-muted-foreground leading-relaxed">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-foreground">Privacy Policy</h1>
        <p>Last updated: July 5, 2026</p>
      </div>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-foreground">Overview</h2>
        <p>
          Blender Skills is an open-source plugin for Claude Code, Cursor, and Kiro. It runs entirely
          on your local machine and does not collect, store, or transmit any personal data.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-foreground">Data Collection</h2>
        <p>
          Blender Skills collects <strong className="text-foreground">no data</strong>. There is no backend,
          no analytics, no telemetry, and no user accounts. The plugin consists entirely of
          local skill files that run inside your AI coding assistant.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-foreground">Third-Party Services</h2>
        <p>
          This plugin integrates with:
        </p>
        <ul className="list-disc list-inside space-y-1 pl-2">
          <li>
            <strong className="text-foreground">Blender MCP</strong> — runs locally on your machine.
            No data leaves your system.
          </li>
          <li>
            <strong className="text-foreground">Claude Code / Cursor / Kiro</strong> — your prompts
            are processed by those platforms under their own privacy policies.
          </li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-foreground">Open Source</h2>
        <p>
          The full source code is available at{' '}
          <a
            href="https://github.com/arjun988/blender-skills"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline"
          >
            github.com/arjun988/blender-skills
          </a>
          . You can audit exactly what the plugin does.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-foreground">Contact</h2>
        <p>
          Questions? Open an issue on{' '}
          <a
            href="https://github.com/arjun988/blender-skills/issues"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline"
          >
            GitHub Issues
          </a>
          .
        </p>
      </section>
    </div>
  )
}
