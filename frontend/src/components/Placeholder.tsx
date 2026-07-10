// 화면 구현 전 라우팅 골격 확인용 — 각 feature 화면이 채워지면 사용처가 사라진다
export default function Placeholder({ title }: { title: string }) {
  return (
    <main className="p-8">
      <h1 className="text-title-md font-bold">{title}</h1>
      <p className="mt-2 text-text-secondary">구현 예정</p>
    </main>
  )
}
