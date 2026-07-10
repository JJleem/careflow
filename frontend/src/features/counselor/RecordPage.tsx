import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useExtractRecord, useRecord, useSaveRecord } from '../../api/queries/counselor'
import { useMyReservations } from '../../api/queries/reservations'
import { detailMessage } from '../../api/error'
import { formatDate, formatTime } from '../../lib/datetime'
import ErrorState from '../../components/ErrorState'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'

const lines = (s: string) => s.split('\n').map((l) => l.trim()).filter(Boolean)

export default function RecordPage() {
  const { reservationId } = useParams()
  const id = Number(reservationId)
  const record = useRecord(id)
  const reservations = useMyReservations()
  const extract = useExtractRecord()
  const save = useSaveRecord(id)

  const [rawMemo, setRawMemo] = useState('')
  const [summary, setSummary] = useState('')
  const [products, setProducts] = useState('')
  const [recommendations, setRecommendations] = useState('')
  const [followUp, setFollowUp] = useState('')
  const [purchaseLinked, setPurchaseLinked] = useState(false)
  // AI 초안을 한 번이라도 받았으면 llm — 검수·수정해도 초안 출처는 유지 (draft_source)
  const [draftSource, setDraftSource] = useState<'manual' | 'llm'>('manual')

  const reservation = reservations.data?.find((r) => r.id === id)

  if (record.isPending) return <Skeleton className="h-64 rounded-card" />
  if (record.isError) return <ErrorState onRetry={() => record.refetch()} />

  // 저장된 기록 — 읽기 화면
  if (record.data) {
    const r = record.data
    return (
      <div className="flex flex-col gap-4">
        <Link to="/work/today" className="text-caption text-text-secondary hover:text-text">
          ‹ 오늘 일정
        </Link>
        <div className="flex items-center gap-2">
          <h1 className="text-title-md">상담 기록</h1>
          <span className="rounded-pill bg-surface px-2.5 py-0.5 text-caption font-semibold text-text-secondary">
            {r.draft_source === 'llm' ? 'AI 초안 · 검수 완료' : '수기 작성'}
          </span>
        </div>
        {reservation && (
          <p className="text-caption text-text-secondary">
            {formatDate(reservation.start_at)} {formatTime(reservation.start_at)} 상담
          </p>
        )}

        <section className="flex flex-col gap-2 rounded-card bg-card p-5 shadow-card">
          <h2 className="text-caption font-semibold text-text-secondary">요약</h2>
          <p className="whitespace-pre-wrap">{r.summary ?? '—'}</p>
        </section>

        <section className="flex flex-col gap-2 rounded-card bg-card p-5 shadow-card">
          <h2 className="text-caption font-semibold text-text-secondary">관심 제품</h2>
          {r.interested_products.length === 0 ? (
            <p className="text-text-secondary">—</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {r.interested_products.map((p) => (
                <span key={p} className="rounded-pill bg-primary-soft px-2.5 py-0.5 text-caption font-semibold text-primary">
                  {p}
                </span>
              ))}
            </div>
          )}
        </section>

        <section className="flex flex-col gap-2 rounded-card bg-card p-5 shadow-card">
          <h2 className="text-caption font-semibold text-text-secondary">권장 사항</h2>
          {r.recommendations.length === 0 ? (
            <p className="text-text-secondary">—</p>
          ) : (
            <ul className="flex list-disc flex-col gap-1 pl-5">
              {r.recommendations.map((rec) => (
                <li key={rec}>{rec}</li>
              ))}
            </ul>
          )}
        </section>

        <section className="flex flex-col gap-2 rounded-card bg-card p-5 shadow-card">
          <h2 className="text-caption font-semibold text-text-secondary">후속 조치</h2>
          <p className="whitespace-pre-wrap">{r.follow_up ?? '—'}</p>
        </section>

        <details className="rounded-card bg-card p-5 shadow-card">
          <summary className="cursor-pointer text-caption font-semibold text-text-secondary">
            메모 원문 보기
          </summary>
          <p className="mt-3 whitespace-pre-wrap text-caption leading-relaxed text-text-secondary">
            {r.raw_memo}
          </p>
        </details>
      </div>
    )
  }

  // 기록 없음 — 작성 폼
  function applyDraft() {
    extract.mutate(rawMemo, {
      onSuccess: (draft) => {
        setSummary(draft.summary)
        setProducts(draft.interested_products.join('\n'))
        setRecommendations(draft.recommendations.join('\n'))
        setFollowUp(draft.follow_up)
        setPurchaseLinked(draft.purchase_linked)
        setDraftSource('llm')
      },
    })
  }

  function submit() {
    save.mutate({
      raw_memo: rawMemo,
      summary: summary.trim() || null,
      interested_products: lines(products),
      recommendations: lines(recommendations),
      follow_up: followUp.trim() || null,
      purchase_linked: purchaseLinked,
      draft_source: draftSource,
    })
  }

  return (
    <div className="flex flex-col gap-5">
      <Link to="/work/today" className="text-caption text-text-secondary hover:text-text">
        ‹ 오늘 일정
      </Link>
      <div className="flex flex-col gap-1">
        <h1 className="text-title-md">상담 기록 작성</h1>
        {reservation && (
          <p className="text-caption text-text-secondary">
            {formatDate(reservation.start_at)} {formatTime(reservation.start_at)} 상담
          </p>
        )}
      </div>

      <section className="flex flex-col gap-2">
        <Label htmlFor="raw-memo">상담 메모</Label>
        <Textarea
          id="raw-memo"
          className="min-h-40"
          placeholder="상담하며 적은 메모를 그대로 붙여넣어도 돼요. AI가 요약·관심 제품·권장 사항으로 정리해 줘요."
          maxLength={10000}
          value={rawMemo}
          onChange={(e) => setRawMemo(e.target.value)}
        />
        <div className="flex items-center gap-3">
          <Button
            size="sm"
            variant="secondary"
            disabled={!rawMemo.trim() || extract.isPending}
            onClick={applyDraft}
          >
            {extract.isPending ? '정리하는 중…' : 'AI로 구조화'}
          </Button>
          {extract.isError && (
            <p className="text-caption text-text-secondary">
              AI 정리에 실패했어요 — 아래에 직접 작성해도 저장할 수 있어요
            </p>
          )}
        </div>
      </section>

      {/* AI 초안은 어디까지나 초안 — 상담사가 검수·수정한 뒤 저장한다 (§4.5 휴먼 인 더 루프) */}
      <section className="flex flex-col gap-4 rounded-card bg-card p-5 shadow-card">
        <div className="flex items-center justify-between">
          <h2 className="font-bold">기록 내용 {draftSource === 'llm' && <span className="text-caption font-semibold text-primary">— AI 초안, 검수해 주세요</span>}</h2>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="summary">요약</Label>
          <Textarea id="summary" value={summary} onChange={(e) => setSummary(e.target.value)} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="products">관심 제품 (한 줄에 하나)</Label>
          <Textarea
            id="products"
            className="min-h-16"
            value={products}
            onChange={(e) => setProducts(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="recommendations">권장 사항 (한 줄에 하나)</Label>
          <Textarea
            id="recommendations"
            className="min-h-16"
            value={recommendations}
            onChange={(e) => setRecommendations(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="follow-up">후속 조치</Label>
          <Input id="follow-up" value={followUp} onChange={(e) => setFollowUp(e.target.value)} />
        </div>
        <label className="flex items-center gap-2 text-body">
          <input
            type="checkbox"
            className="size-4 accent-[var(--cf-color-primary)]"
            checked={purchaseLinked}
            onChange={(e) => setPurchaseLinked(e.target.checked)}
          />
          상담 중 구매 의사를 확인했어요
        </label>
      </section>

      {save.isError && (
        <p role="alert" className="text-caption text-danger">
          {detailMessage(save.error, '저장하지 못했어요. 잠시 후 다시 시도해 주세요.')}
        </p>
      )}

      <Button className="w-full" disabled={!rawMemo.trim() || save.isPending} onClick={submit}>
        {save.isPending ? '저장 중…' : '기록 저장'}
      </Button>
    </div>
  )
}
