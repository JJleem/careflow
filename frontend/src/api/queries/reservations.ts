import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { components } from '../schema'
import { api } from '../client'
import { apiError } from '../error'

type ReservationCreate = components['schemas']['ReservationCreate']
type ReservationStatus = components['schemas']['ReservationStatus']

export function useAvailableTimes(date: string) {
  return useQuery({
    queryKey: ['slots', date],
    queryFn: async () => {
      const { data, error, response } = await api.GET('/slots', {
        params: { query: { date } },
      })
      if (!data) throw apiError(response, error)
      return data
    },
  })
}

export function useMyReservations(enabled = true) {
  return useQuery({
    queryKey: ['me', 'reservations'],
    enabled,
    queryFn: async () => {
      const { data, error, response } = await api.GET('/me/reservations')
      if (!data) throw apiError(response, error)
      return data
    },
  })
}

/** 409는 예외가 아니라 분기 응답 — ApiError.detail에 만석 대안(alternative_times/dates)이 실려 온다 (docs/06 §6.5) */
export function useCreateReservation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: ReservationCreate) => {
      const { data, error, response } = await api.POST('/reservations', { body })
      if (!data) throw apiError(response, error)
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['slots'] })
      qc.invalidateQueries({ queryKey: ['me', 'reservations'] })
    },
  })
}

export function useTransitionReservation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, status }: { id: number; status: ReservationStatus }) => {
      const { data, error, response } = await api.PATCH('/reservations/{reservation_id}', {
        params: { path: { reservation_id: id } },
        body: { status },
      })
      if (!data) throw apiError(response, error)
      return data
    },
    onSuccess: () => {
      // 상태 전이 → 슬롯·내 예약·알림 무효화 (docs/06 §6.5)
      qc.invalidateQueries({ queryKey: ['slots'] })
      qc.invalidateQueries({ queryKey: ['me', 'reservations'] })
      qc.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}
