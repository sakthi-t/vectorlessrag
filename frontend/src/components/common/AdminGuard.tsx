import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { LoadingSpinner } from "./LoadingSpinner";
import apiClient from "../../api/client";

async function getMeForGuard(): Promise<{ id: string; email: string; role: string }> {
  const { data } = await apiClient.get("/api/v1/auth/me");
  return data;
}

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["admin-guard-check"],
    queryFn: getMeForGuard,
    staleTime: 0,
    retry: 0,
    refetchOnMount: true,
  });

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (isError || !data || data.role !== "admin") {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
