import { useQueries, useQuery } from '@tanstack/react-query'
import { api } from '../client'
import { apiError } from '../error'

// 쿼리 키는 리소스 경로 그대로 (docs/06 §6.5)

export function useSubjects() {
  return useQuery({
    queryKey: ['subjects'],
    queryFn: async () => {
      const { data, error, response } = await api.GET('/subjects')
      if (!data) throw apiError(response, error)
      return data
    },
  })
}

/** 피검자별 결과지 병렬 조회 — 피검자는 본인+가족 소수라 N번 요청이 문제되지 않는다 */
export function useSubjectResults(subjectIds: number[]) {
  return useQueries({
    queries: subjectIds.map((id) => ({
      queryKey: ['subjects', id, 'test-results'],
      queryFn: async () => {
        const { data, error, response } = await api.GET('/subjects/{subject_id}/test-results', {
          params: { path: { subject_id: id } },
        })
        if (!data) throw apiError(response, error)
        return data
      },
    })),
  })
}

export function useTestResult(id: number) {
  return useQuery({
    queryKey: ['test-results', id],
    queryFn: async () => {
      const { data, error, response } = await api.GET('/test-results/{test_result_id}', {
        params: { path: { test_result_id: id } },
      })
      if (!data) throw apiError(response, error)
      return data
    },
  })
}

/** 결과지 상세의 상담 QR — 실물 인쇄분과 동일한 서명 토큰 (docs/04 §4.7 진입점 이원화) */
export function useConsultToken(testResultId: number) {
  return useQuery({
    queryKey: ['test-results', testResultId, 'consult-token'],
    queryFn: async () => {
      const { data, error, response } = await api.GET(
        '/test-results/{test_result_id}/consult-token',
        { params: { path: { test_result_id: testResultId } } },
      )
      if (!data) throw apiError(response, error)
      return data
    },
  })
}
