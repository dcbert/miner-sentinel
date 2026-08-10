import GlobalTimeRange from '@/components/layout/GlobalTimeRange'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/AuthContext'
import { isTimeRangeRoute } from '@/lib/timeRange'
import { cn } from '@/lib/utils'
import {
  Cpu,
  Home,
  LogOut,
  Menu,
  Settings,
  TrendingUp,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

/**
 * App shell design principles (ops / monitoring products):
 * - Persistent left nav for primary destinations (Linear, Vercel, Grafana)
 * - Clear visual hierarchy: brand → primary nav → secondary → account
 * - Active state is calm and scannable (fill + left accent, not neon glow)
 * - Density for daily use; breathing room without empty “marketing” chrome
 * - Header holds context tools (time range), not duplicate identity chrome
 */

const NAV_SECTIONS = [
  {
    id: 'monitor',
    label: 'Monitor',
    items: [
      {
        path: '/',
        label: 'Overview',
        icon: Home,
        match: (p) => p === '/',
      },
      {
        path: '/mining',
        label: 'Mining',
        icon: Cpu,
        match: (p) =>
          p === '/mining' ||
          p.startsWith('/mining/') ||
          p.startsWith('/devices/') ||
          p.startsWith('/bitaxe/') ||
          p.startsWith('/avalon/'),
      },
      {
        path: '/analytics',
        label: 'Analytics',
        icon: TrendingUp,
        match: (p) => p === '/analytics' || p.startsWith('/analytics/'),
      },
    ],
  },
  {
    id: 'system',
    label: 'System',
    items: [
      {
        path: '/settings',
        label: 'Settings',
        icon: Settings,
        match: (p) => p === '/settings' || p.startsWith('/settings/'),
      },
    ],
  },
]

const PAGE_META = {
  '/': {
    title: 'Overview',
    description: 'Fleet health and live performance',
  },
  '/mining': {
    title: 'Mining',
    description: 'Devices, pool stats, and history',
  },
  '/analytics': {
    title: 'Analytics',
    description: 'Predictions, energy, and cost',
  },
  '/settings': {
    title: 'Settings',
    description: 'Devices, pool, and notifications',
  },
}

function resolvePageMeta(pathname) {
  if (PAGE_META[pathname]) return PAGE_META[pathname]
  if (
    pathname.startsWith('/devices/') ||
    pathname.startsWith('/bitaxe/') ||
    pathname.startsWith('/avalon/')
  ) {
    return {
      title: 'Device',
      description: 'Hardware detail and trends',
    }
  }
  for (const [path, meta] of Object.entries(PAGE_META)) {
    if (path !== '/' && pathname.startsWith(path)) return meta
  }
  return { title: 'Dashboard', description: null }
}

function isNavActive(item, pathname) {
  return item.match(pathname)
}

export default function Layout({ children }) {
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { user, logout } = useAuth()
  const showTimeRange = isTimeRangeRoute(location.pathname)
  const page = resolvePageMeta(location.pathname)

  const handleLogout = () => {
    logout()
    window.location.href = '/login'
  }

  const initials = (user?.username || 'U').slice(0, 2).toUpperCase()

  const sidebar = (
    <>
      {/* Brand */}
      <div className="flex h-14 shrink-0 items-center gap-2.5 border-b border-border/80 px-4">
        <Link
          to="/"
          onClick={() => setMobileMenuOpen(false)}
          className="group flex min-w-0 items-center gap-2.5 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <img
            src="/logo.svg"
            alt=""
            width={28}
            height={28}
            className="h-7 w-7 shrink-0 rounded-md object-cover"
            draggable={false}
          />
          <span className="truncate text-[13px] font-semibold tracking-tight text-foreground">
            MinerSentinel
          </span>
        </Link>
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto h-8 w-8 shrink-0 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-label="Close menu"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Main">
        <div className="space-y-5">
          {NAV_SECTIONS.map((section) => (
            <div key={section.id}>
              <p className="mb-1.5 px-2 text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground/80">
                {section.label}
              </p>
              <ul className="space-y-0.5">
                {section.items.map((item) => {
                  const Icon = item.icon
                  const active = isNavActive(item, location.pathname)
                  return (
                    <li key={item.path}>
                      <Link
                        to={item.path}
                        onClick={() => setMobileMenuOpen(false)}
                        aria-current={active ? 'page' : undefined}
                        className={cn(
                          'group relative flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] outline-none transition-colors',
                          'focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                          active
                            ? 'bg-accent font-medium text-accent-foreground'
                            : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground',
                        )}
                      >
                        {/* Active rail — subtle orientation cue */}
                        <span
                          className={cn(
                            'absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full transition-opacity',
                            active ? 'bg-foreground opacity-100' : 'opacity-0',
                          )}
                          aria-hidden
                        />
                        <Icon
                          className={cn(
                            'h-[15px] w-[15px] shrink-0 transition-opacity',
                            active ? 'opacity-100' : 'opacity-70 group-hover:opacity-100',
                          )}
                          strokeWidth={1.75}
                        />
                        <span className="truncate">{item.label}</span>
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </div>
      </nav>

      {/* Account */}
      <div className="shrink-0 border-t border-border/80 p-3">
        <div className="flex items-center gap-2.5 rounded-lg px-1.5 py-1">
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-muted text-[11px] font-semibold tabular-nums text-muted-foreground"
            aria-hidden
          >
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] font-medium leading-tight text-foreground">
              {user?.username || 'User'}
            </p>
            {user?.email ? (
              <p className="truncate text-[11px] leading-tight text-muted-foreground">
                {user.email}
              </p>
            ) : (
              <p className="truncate text-[11px] leading-tight text-muted-foreground">
                Signed in
              </p>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0 text-muted-foreground hover:text-foreground"
            onClick={handleLogout}
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut className="h-3.5 w-3.5" strokeWidth={1.75} />
          </Button>
        </div>
      </div>
    </>
  )

  return (
    <div className="min-h-screen bg-background safe-top safe-bottom">
      {/* Desktop sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r border-border/80',
          'bg-muted/30 dark:bg-muted/20',
          'md:flex',
        )}
      >
        {sidebar}
      </aside>

      {/* Mobile drawer */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-[min(16.5rem,85vw)] flex-col border-r border-border bg-background shadow-xl transition-transform duration-200 ease-out md:hidden',
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {sidebar}
      </aside>

      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/60 backdrop-blur-[2px] md:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden
        />
      )}

      {/* Main column */}
      <div className="md:pl-60">
        {/* Mobile header */}
        <header className="sticky top-0 z-30 border-b border-border/80 bg-background/90 backdrop-blur-md md:hidden">
          <div className="flex h-14 items-center gap-3 px-3">
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 shrink-0"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold leading-none">
                {page.title}
              </p>
              {page.description && (
                <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
                  {page.description}
                </p>
              )}
            </div>
          </div>
          {showTimeRange && (
            <div className="border-t border-border/60 px-3 py-2">
              <GlobalTimeRange compact className="w-full" />
            </div>
          )}
        </header>

        {/* Desktop header */}
        <header className="sticky top-0 z-30 hidden border-b border-border/80 bg-background/90 backdrop-blur-md md:block">
          <div className="flex h-14 items-center justify-between gap-6 px-6">
            <div className="min-w-0">
              <h1 className="truncate text-sm font-semibold tracking-tight text-foreground">
                {page.title}
              </h1>
              {page.description && (
                <p className="truncate text-[12px] text-muted-foreground">
                  {page.description}
                </p>
              )}
            </div>
            {showTimeRange && (
              <div className="shrink-0">
                <GlobalTimeRange />
              </div>
            )}
          </div>
        </header>

        <main className="p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  )
}
