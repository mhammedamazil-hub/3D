import { Sidebar } from '@/components/sidebar'

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-w-screen-2xl mx-auto flex px-4 md:px-6">
      <Sidebar />
      <main className="flex-1 min-w-0 py-8 lg:pl-10">
        {children}
      </main>
    </div>
  )
}
