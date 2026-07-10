import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import RequireRole from './auth/RequireRole'
import LoginPage from './auth/LoginPage'
import SignupPage from './auth/SignupPage'
import { roleHome, useAuthStore } from './auth/store'
import ConsultEntryPage from './features/consult/ConsultEntryPage'
import ResultsListPage from './features/customer/ResultsListPage'
import ResultDetailPage from './features/customer/ResultDetailPage'
import ReservePage from './features/customer/ReservePage'
import MyReservationsPage from './features/customer/MyReservationsPage'
import NotificationsPage from './features/customer/NotificationsPage'
import TodayPage from './features/counselor/TodayPage'
import RecordPage from './features/counselor/RecordPage'
import SlotsPage from './features/counselor/SlotsPage'
import DashboardPage from './features/admin/DashboardPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

function RootRedirect() {
  const user = useAuthStore((s) => s.user)
  return <Navigate to={user ? roleHome[user.role] : '/login'} replace />
}

// 라우팅 맵: docs/06 §6.3
const router = createBrowserRouter([
  { path: '/', element: <RootRedirect /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/signup', element: <SignupPage /> },
  { path: '/consult', element: <ConsultEntryPage /> },
  {
    element: <RequireRole roles={['customer']} />,
    children: [
      { path: '/results', element: <ResultsListPage /> },
      { path: '/results/:id', element: <ResultDetailPage /> },
      { path: '/my/reservations', element: <MyReservationsPage /> },
      { path: '/notifications', element: <NotificationsPage /> },
    ],
  },
  {
    // 예약은 로그인 고객 + QR 스코프 세션 둘 다 진입 (docs/06 §6.3)
    element: <RequireRole roles={['customer']} allowScopedSession />,
    children: [{ path: '/reserve', element: <ReservePage /> }],
  },
  {
    element: <RequireRole roles={['counselor']} />,
    children: [
      { path: '/work/today', element: <TodayPage /> },
      { path: '/work/records/:reservationId', element: <RecordPage /> },
      { path: '/work/slots', element: <SlotsPage /> },
    ],
  },
  {
    element: <RequireRole roles={['admin']} />,
    children: [{ path: '/admin', element: <DashboardPage /> }],
  },
  { path: '*', element: <RootRedirect /> },
])

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}
