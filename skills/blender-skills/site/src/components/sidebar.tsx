'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import { sidebarSections } from '@/lib/nav'

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="hidden lg:block w-60 shrink-0 sticky top-14 h-[calc(100vh-3.5rem)] overflow-y-auto border-r py-6 pr-4">
      <nav className="space-y-6">
        {sidebarSections.map((section) => (
          <div key={section.title}>
            <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {section.title}
            </p>
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const isActive = pathname === item.href
                const isExternal = 'external' in item && item.external

                return (
                  <li key={item.href + item.title}>
                    <Link
                      href={item.href}
                      target={isExternal ? '_blank' : undefined}
                      rel={isExternal ? 'noopener noreferrer' : undefined}
                      className={cn(
                        'flex items-center gap-1 rounded-md px-3 py-1.5 text-sm transition-colors hover:bg-accent hover:text-accent-foreground',
                        isActive
                          ? 'bg-primary/10 text-primary font-medium'
                          : 'text-foreground/70'
                      )}
                    >
                      <span className="flex-1">{item.title}</span>
                      {isExternal && <ExternalLink className="h-3 w-3 opacity-50" />}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  )
}
