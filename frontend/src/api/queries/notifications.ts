import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../client'
import { apiError } from '../error'

/** 인앱 채널 수신 폴링 30초 — 백엔드 발송 주기 60초와 짝 (docs/06 §6.5) */
export function useNotifications(enabled = true) {
  return useQuery({
    queryKey: ['notifications'],
    enabled,
    refetchInterval: 30_000,
    queryFn: async () => {
      const { data, error, response } = await api.GET('/notifications')
      if (!data) throw apiError(response, error)
      return data
    },
  })
}

export function useMarkRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      const { data, error, response } = await api.PATCH('/notifications/{notification_id}/read', {
        params: { path: { notification_id: id } },
      })
      if (!data) throw apiError(response, error)
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })
}
