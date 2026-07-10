import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import { roleHome, useAuthStore } from '@/auth/store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    const { data, response } = await api.POST('/auth/login', {
      body: { email, password },
    })
    setSubmitting(false)
    if (data) {
      login(data.access_token, data.user)
      navigate(roleHome[data.user.role], { replace: true })
      return
    }
    setError(
      response.status === 401
        ? '이메일 또는 비밀번호가 올바르지 않습니다.'
        : '로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.',
    )
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-title-md">CareFlow 로그인</CardTitle>
          <CardDescription>검사 결과 확인과 상담 예약을 시작하세요</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">이메일</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">비밀번호</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && (
              <p role="alert" className="text-caption text-danger">
                {error}
              </p>
            )}
            <Button type="submit" disabled={submitting || !email || !password}>
              {submitting ? '로그인 중…' : '로그인'}
            </Button>
          </form>
          <p className="mt-4 text-center text-caption text-text-secondary">
            계정이 없으신가요?{' '}
            <Link to="/signup" className="text-primary underline underline-offset-2">
              회원가입
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  )
}
