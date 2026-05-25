import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ClerkProvider } from '@clerk/clerk-react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, useNavigate } from 'react-router-dom'
import './index.css'
import App from './App.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
})

function ClerkWithRouter({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
  return (
    <ClerkProvider
      publishableKey={publishableKey}
      routerPush={(to) => navigate(to)}
      routerReplace={(to) => navigate(to, { replace: true })}
      afterSignOutUrl="/sign-in"
    >
      {children}
    </ClerkProvider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ClerkWithRouter>
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      </ClerkWithRouter>
    </BrowserRouter>
  </StrictMode>,
)
