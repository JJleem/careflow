import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import type { components } from '../schema'
import { api } from '../client'
import { apiError } from '../error'

type RecordSaveRequest = components['schemas']['RecordSaveRequest']

export function useMySlots(dateFrom: string, dateTo: string) {
  return useQuery({
    queryKey: ['me', 'slots', dateFrom, dateTo],
    queryFn: async () => {
      const { data, error, response } = await api.GET('/me/slots', {
        params: { query: { date_from: dateFrom, date_to: dateTo } },
      })
      if (!data) throw apiError(response, error)
      return data
    },
  })
}

export function useCreateSlot() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (startAt: string) => {
      const { data, error, response } = await api.POST('/me/slots', {
        body: { start_at: startAt },
      })
      if (!data) throw apiError(response, error)
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me', 'slots'] }),
  })
}

export function useDeleteSlot() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (slotId: number) => {
      const { error, response } = await api.DELETE('/me/slots/{slot_id}', {
        params: { path: { slot_id: slotId } },
      })
      if (!response.ok) throw apiError(response, error)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me', 'slots'] }),
  })
}

/** 당일 예약들의 브리핑 병렬 조회 — 404(브리핑 없음)는 에러가 아니라 '없음'으로 다룬다 */
export function useBriefings(reservationIds: number[]) {
  return useQueries({
    queries: reservationIds.map((id) => ({
      queryKey: ['reservations', id, 'briefing'],
      retry: false,
      queryFn: async () => {
        const { data, error, response } = await api.GET(
          '/reservations/{reservation_id}/briefing',
          { params: { path: { reservation_id: id } } },
        )
        if (response.status === 404) return null
        if (!data) throw apiError(response, error)
        return data
      },
    })),
  })
}

export function useRecord(reservationId: number) {
  return useQuery({
    queryKey: ['reservations', reservationId, 'record'],
    retry: false,
    queryFn: async () => {
      const { data, error, response } = await api.GET('/reservations/{reservation_id}/record', {
        params: { path: { reservation_id: reservationId } },
      })
      if (response.status === 404) return null // 아직 기록 없음 — 작성 폼을 연다
      if (!data) throw apiError(response, error)
      return data
    },
  })
}

/** 메모 → 구조화 초안 (동기 LLM). 실패해도 수기 작성 경로는 그대로 (NFR-3) */
export function useExtractRecord() {
  return useMutation({
    mutationFn: async (rawMemo: string) => {
      const { data, error, response } = await api.POST('/records/extract', {
        body: { raw_memo: rawMemo },
      })
      if (!data) throw apiError(response, error)
      return data
    },
  })
}

export function useSaveRecord(reservationId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: RecordSaveRequest) => {
      const { data, error, response } = await api.POST('/reservations/{reservation_id}/record', {
        params: { path: { reservation_id: reservationId } },
        body,
      })
      if (!data) throw apiError(response, error)
      return data
    },
    onSuccess: (data) =>
      qc.setQueryData(['reservations', reservationId, 'record'], data),
  })
}
