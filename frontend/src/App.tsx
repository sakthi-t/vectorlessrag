import {
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  useAuth,
} from "@clerk/clerk-react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AppShell } from "./components/layout/AppShell";
import { AdminGuard } from "./components/common/AdminGuard";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { ChatPage } from "./pages/ChatPage";
import { ProfilePage } from "./pages/ProfilePage";
import { AdminDashboardPage } from "./pages/admin/AdminDashboardPage";
import { useEffect } from "react";
import { setTokenProvider } from "./api/client";

function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth();

  useEffect(() => {
    setTokenProvider(() => getToken({ skipCache: false }));
  }, [getToken]);

  return <AppShell>{children}</AppShell>;
}

export default function App() {
  return (
    <>
      <Toaster position="top-right" toastOptions={{ duration: 4000 }} />

      <SignedOut>
        <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
          <div className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-lg">
            <h1 className="mb-6 text-center text-2xl font-bold text-gray-900">
              Vectorless RAG
            </h1>
            <p className="mb-6 text-center text-sm text-gray-500">
              Sign in to upload documents and ask questions.
            </p>
            <div className="space-y-3">
              <SignInButton mode="modal">
                <button className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700">
                  Sign In
                </button>
              </SignInButton>
              <SignUpButton mode="modal">
                <button className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50">
                  Sign Up
                </button>
              </SignUpButton>
            </div>
          </div>
        </div>
      </SignedOut>

      <SignedIn>
        <Routes>
          <Route
            path="/"
            element={
              <ProtectedLayout>
                <DashboardPage />
              </ProtectedLayout>
            }
          />
          <Route
            path="/documents"
            element={
              <ProtectedLayout>
                <DocumentsPage />
              </ProtectedLayout>
            }
          />
          <Route
            path="/chat"
            element={
              <ProtectedLayout>
                <ChatPage />
              </ProtectedLayout>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedLayout>
                <ProfilePage />
              </ProtectedLayout>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedLayout>
                <AdminGuard>
                  <AdminDashboardPage />
                </AdminGuard>
              </ProtectedLayout>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </SignedIn>
    </>
  );
}
