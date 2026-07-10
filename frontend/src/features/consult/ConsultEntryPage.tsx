import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useConsultInfo, useVerifyConsult } from '../../api/queries/consult'
import { ApiError } from '../../api/error'
import { SERVICE_TYPE_LABEL } from '../../lib/labels'
import { formatDateOnly } from '../../lib/datetime'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'

/** QR 스캔 진입: 토큰 서명 검증 → 이름+전화 본인확인 → 30분 스코프 세션으로 예약 화면 이동.
 *  로그인 없이 쓰는 공개 라우트 — 결과지를 손에 든 사람만 통과할 수 있게 설계됐다 (docs/04 §4.7). */
export default function ConsultEntryPage() {
  const [params] = useSearchParams()
  const token = params.get('t') ?? ''
  const navigate = useNavigate()
  const info = useConsultInfo(token)
  const verify = useVerifyConsult()
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')

  const invalid = !token || info.isError

  function submit(e: React.FormEvent) {
    e.preventDefault()
    verify.mutate(
      { token, name, phone },
      { onSuccess: () => navigate('/reserve', { replace: true }) },
    )
  }

  const verifyError =
    verify.error instanceof ApiError
      ? verify.error.status === 403
        ? '이름 또는 전화번호가 결과지 정보와 일치하지 않아요.'
        : verify.error.status === 429
          ? '시도 횟수를 초과했어요. 잠시 후 다시 시도해 주세요.'
          : '유효하지 않은 QR 코드예요. 결과지의 QR을 다시 스캔해 주세요.'
      : null

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface p-4">
      <Card className="w-full max-w-sm gap-7 py-8">
        {invalid ? (
          <CardContent className="flex flex-col items-center gap-3 text-center">
            <CardTitle asChild className="text-title-md font-bold tracking-[-0.02em]">
              <h1>QR 코드를 확인할 수 없어요</h1>
            </CardTitle>
            <CardDescription>
              유효 기간이 지났거나 손상된 링크예요. 결과지의 QR을 다시 스캔하거나, 로그인해서
              예약해 주세요.
            </CardDescription>
            <Button asChild variant="secondary" size="sm" className="mt-2">
              <Link to="/login">로그인으로 예약하기</Link>
            </Button>
          </CardContent>
        ) : info.isPending ? (
          <CardContent>
            <Skeleton className="h-40 rounded-card" />
          </CardContent>
        ) : (
          <>
            <CardHeader className="gap-1.5">
              <p className="text-caption font-bold text-primary">CareFlow</p>
              <CardTitle asChild className="text-title-md font-bold tracking-[-0.02em]">
                <h1>본인확인이 필요해요</h1>
              </CardTitle>
              <CardDescription>
                {info.data.subject_name_masked}님의 {SERVICE_TYPE_LABEL[info.data.service_type]} (
                {formatDateOnly(info.data.reported_at)} 발행) 상담 예약이에요. 결과지의 성함과
                검사 신청 시 전화번호를 입력해 주세요.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="name">이름</Label>
                  <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="phone">휴대전화</Label>
                  <Input
                    id="phone"
                    type="tel"
                    placeholder="010-0000-0000"
                    required
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </div>
                {verifyError && (
                  <p role="alert" className="text-caption text-danger">
                    {verifyError}
                  </p>
                )}
                <Button type="submit" disabled={verify.isPending || !name || !phone}>
                  {verify.isPending ? '확인 중…' : '확인하고 예약하기'}
                </Button>
              </form>
            </CardContent>
          </>
        )}
      </Card>
    </main>
  )
}
