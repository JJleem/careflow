import { clsx, type ClassValue } from 'clsx'
import { extendTailwindMerge } from 'tailwind-merge'

// docs/05 타입 스케일 토큰을 폰트 크기 그룹으로 등록 —
// 미등록 시 tailwind-merge가 text-body 등을 "색상"으로 오인해
// text-primary-foreground 같은 진짜 색상 클래스를 제거한다
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      'font-size': [
        'text-title-lg',
        'text-title-md',
        'text-title-sm',
        'text-body',
        'text-caption',
        'text-metric',
      ],
    },
  },
})

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
