import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../client'
import { apiError } from '../error'
import { setScopedSession } from '../../auth/scopedSession'

/** QR 스캔 직후 토큰 서명 검증 — 본인확인 화면에 띄울 최소 정보(마스킹된 이름 등) */
export function useConsultInfo(token: string) {
  return useQuery({
    queryKey: ['consult', token],
    retry: false, // 위변조 토큰은 재시도 무의미
    queryFn: async () => {
      const { data, error, response } = await api.GET('/consult', {
        params: { query: { t: token } },
      })
      if (!data) throw apiError(response, error)
      return data
    },
  })
}

/** 이름+전화 본인확인 → 30분 스코프 세션 발급, sessionStorage에 저장 (docs/06 §6.4) */
export function useVerifyConsult() {
  return useMutation({
    mutationFn: async (body: { token: string; name: string; phone: string }) => {
      const { data, error, response } = await api.POST('/consult/verify', { body })
      if (!data) throw apiError(response, error)
      setScopedSession({
        token: data.access_token,
        testResultId: data.test_result_id,
        subjectId: data.subject_id,
      })
      return data
    },
  })
}
