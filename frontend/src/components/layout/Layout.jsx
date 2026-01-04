import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/AuthContext'
import { cn } from '@/lib/utils'
import { Activity, ChevronRight, Cpu, Home, LogOut, Menu, Settings, Shield, TrendingUp, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

export default function Layout({ children }) {
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { user, logout } = useAuth()

  const navItems = [
    { path: '/', label: 'Overview', icon: Home, description: 'System overview' },
    { path: '/mining', label: 'Mining', icon: Cpu, description: 'Device stats' },
    { path: '/analytics', label: 'Analytics', icon: TrendingUp, description: 'Performance data' },
    { path: '/settings', label: 'Settings', icon: Settings, description: 'Configuration' },
  ]

  const currentPage = navItems.find((item) => item.path === location.pathname)
  const CurrentIcon = currentPage?.icon || Home

  const handleLogout = () => {
    logout()
    window.location.href = '/login'
  }

  // Get user initials for avatar
  const getUserInitials = () => {
    if (user?.username) {
      return user.username.substring(0, 2).toUpperCase()
    }
    return 'U'
  }

  return (
    <div className="min-h-screen bg-background safe-top safe-bottom">
      {/* Sidebar */}
      <aside className={cn(
        "fixed left-0 top-0 z-40 h-screen w-72 border-r bg-card/50 backdrop-blur-xl transition-transform duration-300 ease-in-out",
        mobileMenuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      )}>
        {/* Header with logo */}
        <div className="flex h-16 items-center justify-between border-b px-5">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center shadow-lg shadow-primary/25">
                <Shield className="h-5 w-5 text-primary-foreground" />
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-green-500 border-2 border-card animate-pulse" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">MinerSentinel</h1>
              <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">Mining Monitor</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden h-8 w-8"
            onClick={() => setMobileMenuOpen(false)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col h-[calc(100vh-4rem)]">
          <div className="p-3 space-y-1 flex-1">
            <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Navigation
            </p>
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    "group flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-200",
                    isActive
                      ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25"
                      : "hover:bg-accent/50 text-muted-foreground hover:text-foreground"
                  )}
                >
                  <div className={cn(
                    "flex items-center justify-center w-9 h-9 rounded-lg transition-colors",
                    isActive
                      ? "bg-primary-foreground/20"
                      : "bg-muted/50 group-hover:bg-accent"
                  )}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{item.label}</p>
                    <p className={cn(
                      "text-[10px] truncate",
                      isActive ? "text-primary-foreground/70" : "text-muted-foreground"
                    )}>
                      {item.description}
                    </p>
                  </div>
                  <ChevronRight className={cn(
                    "h-4 w-4 opacity-0 -translate-x-2 transition-all",
                    isActive && "opacity-100 translate-x-0"
                  )} />
                </Link>
              )
            })}
          </div>

          {/* Bottom section container */}
          <div className="mt-auto">
            {/* Status indicator */}
            <div className="px-3 py-2">
              <div className="rounded-xl bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/20 p-3">
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-green-500" />
                  <span className="text-xs font-medium text-green-600 dark:text-green-400">System Online</span>
                </div>
                <p className="text-[10px] text-muted-foreground mt-1">All services running</p>
              </div>
            </div>

            {/* User section */}
            <div className="p-3 border-t bg-muted/30">
              <div className="flex items-center gap-3 p-2 rounded-xl bg-background/50 mb-2">
                <div className="relative">
                  <div className="w-10 h-10 rounded-xl gradient-avatar flex items-center justify-center text-white font-semibold text-sm shadow-md">
                    {getUserInitials()}
                  </div>
                  <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-green-500 border-2 border-background" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-foreground truncate">
                    {user?.username || 'User'}
                  </p>
                  <p className="text-[10px] text-muted-foreground truncate">
                    {user?.email || 'Administrator'}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                className="w-full justify-start gap-3 h-10 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-xl transition-colors"
                onClick={handleLogout}
              >
                <LogOut className="h-4 w-4" />
                <span className="text-sm">Sign Out</span>
              </Button>
            </div>
          </div>
        </nav>
      </aside>

      {/* Main content */}
      <div className="md:pl-72">
        {/* Mobile Header - integrated hamburger menu */}
        <header className="sticky top-0 z-30 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 shadow-sm md:hidden">
          <div className="flex h-14 items-center px-4">
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 shrink-0"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </Button>

            <div className="flex-1 flex items-center justify-center gap-2">
              <CurrentIcon className="h-4 w-4 text-primary" />
              <span className="font-semibold text-base">
                {currentPage?.label || 'Dashboard'}
              </span>
            </div>

            <div className="h-9 w-9 shrink-0 flex items-center justify-center">
              <div className="w-7 h-7 rounded-lg gradient-avatar flex items-center justify-center text-white text-xs font-semibold">
                {getUserInitials()}
              </div>
            </div>
          </div>
        </header>

        {/* Desktop Header */}
        <header className="sticky top-0 z-30 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 shadow-sm hidden md:block">
          <div className="flex h-16 items-center justify-between px-6">
            <div>
              <h2 className="text-lg font-semibold">{currentPage?.label || 'Dashboard'}</h2>
              <p className="text-xs text-muted-foreground">{currentPage?.description || 'System overview'}</p>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted/50">
                <div className="w-6 h-6 rounded-md gradient-avatar flex items-center justify-center text-white text-[10px] font-semibold">
                  {getUserInitials()}
                </div>
                <span className="text-sm font-medium">{user?.username || 'User'}</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-9 w-9 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg"
                onClick={handleLogout}
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </header>

        <main className="p-3 sm:p-6">
          {children}
        </main>
      </div>

      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-30 bg-background/80 backdrop-blur-sm md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}
    </div>
  )
}
