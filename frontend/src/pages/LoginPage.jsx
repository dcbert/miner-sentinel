import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from '@/components/ui/toaster'
import api from '@/lib/api'
import { cn } from '@/lib/utils'
import { Eye, EyeOff, Loader2, Lock, User } from 'lucide-react'
import { useEffect, useState } from 'react'

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  useEffect(() => {
    const fetchCsrfToken = async () => {
      try {
        await api.get('/api/auth/csrf/')
      } catch (error) {
        console.error('Failed to fetch CSRF token:', error)
      }
    }
    fetchCsrfToken()
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const response = await api.post('/api/auth/login/', { username, password })
      if (response.data.success) {
        toast({
          title: 'Signed in',
          description: 'Welcome back to MinerSentinel',
        })
        onLogin({
          token: response.data.token || 'session-active',
          user: response.data.user,
        })
      }
    } catch (error) {
      toast({
        title: 'Sign-in failed',
        description:
          error.response?.data?.error ||
          error.response?.data?.detail ||
          'Invalid username or password',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="relative min-h-screen bg-background text-foreground">
      {/* Subtle ambient background — same calm density as the app shell */}
      <div
        className="pointer-events-none absolute inset-0 overflow-hidden"
        aria-hidden
      >
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_color-mix(in oklch, var(--muted) 45%, transparent)_0%,_transparent_55%)]" />
        <div
          className="absolute inset-0 opacity-[0.035] dark:opacity-[0.06]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M40 0H0V40' fill='none' stroke='%23fff' stroke-width='0.5'/%3E%3C/svg%3E")`,
          }}
        />
      </div>

      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center px-4 py-10">
        <div className="w-full max-w-[400px] space-y-8">
          {/* Brand */}
          <div className="flex flex-col items-center text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl border border-border/80 bg-card shadow-sm">
              <img
                src="/logo.svg"
                alt="MinerSentinel"
                width={40}
                height={40}
                className="h-10 w-10 rounded-md object-cover"
                draggable={false}
              />
            </div>
            <h1 className="text-xl font-semibold tracking-tight text-foreground">
              MinerSentinel
            </h1>
            <p className="mt-1.5 max-w-xs text-sm text-muted-foreground">
              Self-hosted monitoring for home Bitcoin miners
            </p>
          </div>

          {/* Login card */}
          <Card className="border-border/80 shadow-sm">
            <CardHeader className="space-y-1 pb-4">
              <CardTitle className="text-lg font-semibold tracking-tight">
                Sign in
              </CardTitle>
              <CardDescription>
                Enter your credentials to open the dashboard
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="username">Username</Label>
                  <div className="relative">
                    <User
                      className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                      strokeWidth={1.75}
                      aria-hidden
                    />
                    <Input
                      id="username"
                      name="username"
                      type="text"
                      autoComplete="username"
                      autoFocus
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="pl-9"
                      placeholder="Username"
                      required
                      disabled={isLoading}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Lock
                      className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                      strokeWidth={1.75}
                      aria-hidden
                    />
                    <Input
                      id="password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="pl-9 pr-10"
                      placeholder="Password"
                      required
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      className={cn(
                        'absolute right-1.5 top-1/2 -translate-y-1/2 flex h-9 w-9 items-center justify-center rounded-md',
                        'text-muted-foreground hover:text-foreground',
                        'outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      )}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      tabIndex={0}
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" strokeWidth={1.75} />
                      ) : (
                        <Eye className="h-4 w-4" strokeWidth={1.75} />
                      )}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full"
                  disabled={isLoading || !username || !password}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Signing in…
                    </>
                  ) : (
                    'Sign in'
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          <p className="text-center text-[11px] text-muted-foreground/80">
            Local dashboard · your data stays on this host
          </p>
        </div>
      </div>
    </main>
  )
}