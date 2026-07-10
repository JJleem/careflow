import { useQuery } from '@tanstack/react-query'
import { api } from '../client'
import { apiError } from '../error'

/** 기간 지표 (docs/06 §6.5). 쿼리 키에 from/to 포함 — 기간 바꾸면 별도 캐시 */
export function useMetrics(from: string, to: string) {
  return useQuery({
    queryKey: ['admin', 'metrics', from, to],
    queryFn: async () => {
      const { data, error, response } = await api.GET('/admin/metrics', {
        params: { query: { from, to } },
      })
      if (!data) throw apiError(response, error)
      return data
    },
  })
}
