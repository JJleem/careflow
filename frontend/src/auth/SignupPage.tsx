import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import { roleHome, useAuthStore } from '@/auth/store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function SignupPage() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const [form, setForm] = useState({ email: '', password: '', name: '', phone: '' })
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    const { data, response } = await api.POST('/auth/signup', { body: form })
    setSubmitting(false)
    if (data) {
      // 가입 즉시 토큰이 오므로 로그인 화면을 거치지 않고 역할 홈으로
      login(data.access_token, data.user)
      navigate(roleHome[data.user.role], { replace: true })
      return
    }
    setError(
      response.status === 409
        ? '이미 가입된 이메일이에요. 로그인으로 이동해 주세요.'
        : response.status === 422
          ? '입력한 정보를 다시 확인해 주세요.'
          : '일시적인 오류예요. 잠시 후 다시 시도해 주세요.',
    )
  }

  const filled = Object.values(form).every(Boolean)

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface p-4">
      <Card className="w-full max-w-sm gap-7 py-8">
        <CardHeader className="gap-1.5">
          <p className="text-caption font-bold text-primary">CareFlow</p>
          <CardTitle className="text-title-md font-bold tracking-[-0.02em]">
            만나서 반가워요
          </CardTitle>
          <CardDescription>검사 키트를 구매할 때 사용한 정보로 가입해 주세요</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
            <div className="flex flex-col gap-2">
              <Label htmlFor="name">이름</Label>
              <Input id="name" autoComplete="name" required value={form.name} onChange={set('name')} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="phone">휴대전화</Label>
              <Input
                id="phone"
                type="tel"
                autoComplete="tel"
                placeholder="010-0000-0000"
                required
                value={form.phone}
                onChange={set('phone')}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">이메일</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="name@example.com"
                required
                value={form.email}
                onChange={set('email')}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">비밀번호</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                required
                value={form.password}
                onChange={set('password')}
              />
            </div>
            {error && (
              <p role="alert" className="text-caption text-danger">
                {error}
              </p>
            )}
            <Button type="submit" disabled={submitting || !filled}>
              {submitting ? '가입 중…' : '가입하기'}
            </Button>
          </form>
          <p className="mt-4 text-center text-caption text-text-secondary">
            이미 계정이 있으신가요?{' '}
            <Link to="/login" className="text-primary underline underline-offset-2">
              로그인
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  )
}
