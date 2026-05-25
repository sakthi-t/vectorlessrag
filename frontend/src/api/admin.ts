import apiClient from "./client";
import type { AdminStats, AdminUser } from "../types";

export async function getAdminStats(): Promise<AdminStats> {
  const { data } = await apiClient.get("/api/v1/admin/stats");
  return data;
}

export async function getAdminUsers(): Promise<AdminUser[]> {
  const { data } = await apiClient.get("/api/v1/admin/users");
  return data;
}

export async function deleteUser(userId: string): Promise<void> {
  await apiClient.delete(`/api/v1/admin/users/${userId}`);
}
