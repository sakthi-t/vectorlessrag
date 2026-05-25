import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { getAdminStats, getAdminUsers, deleteUser } from "../../api/admin";
import { LoadingSpinner } from "../../components/common/LoadingSpinner";
import { Trash2, Users, FileText, HardDrive } from "lucide-react";
import apiClient from "../../api/client";
import type { AdminUser } from "../../types";

async function getMe(): Promise<{ id: string }> {
  const { data } = await apiClient.get("/api/v1/auth/me");
  return data;
}

export function AdminDashboardPage() {
  const { data: stats } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: getAdminStats,
  });

  const { data: users, isLoading: usersLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: getAdminUsers,
  });

  const { data: me } = useQuery({
    queryKey: ["admin-guard-check"],
    queryFn: getMe,
    staleTime: 0,
  });

  const queryClient = useQueryClient();
  const [confirmUser, setConfirmUser] = useState<AdminUser | null>(null);

  const deleteMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      queryClient.invalidateQueries({ queryKey: ["admin-stats"] });
      toast.success("User deleted successfully");
      setConfirmUser(null);
    },
    onError: () => {
      toast.error("Failed to delete user. Please try again.");
      setConfirmUser(null);
    },
  });

  const storageGB = stats
    ? (stats.total_storage_bytes / (1024 ** 3)).toFixed(2)
    : "0";

  return (
    <div>
      <h2 className="mb-6 text-2xl font-bold text-gray-900">Admin Dashboard</h2>

      <div className="mb-8 grid gap-6 sm:grid-cols-3">
        <div className="flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="rounded-lg bg-blue-100 p-3">
            <Users className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <p className="text-sm text-gray-500">Total Users</p>
            <p className="text-2xl font-bold text-gray-900">
              {stats?.total_users ?? "-"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="rounded-lg bg-green-100 p-3">
            <FileText className="h-6 w-6 text-green-600" />
          </div>
          <div>
            <p className="text-sm text-gray-500">Total Documents</p>
            <p className="text-2xl font-bold text-gray-900">
              {stats?.total_documents ?? "-"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="rounded-lg bg-purple-100 p-3">
            <HardDrive className="h-6 w-6 text-purple-600" />
          </div>
          <div>
            <p className="text-sm text-gray-500">Storage Used</p>
            <p className="text-2xl font-bold text-gray-900">{storageGB} GB</p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white">
        <div className="border-b border-gray-200 px-6 py-4">
          <h3 className="font-semibold text-gray-900">User Management</h3>
        </div>
        {usersLoading ? (
          <div className="p-8">
            <LoadingSpinner />
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 text-left text-sm text-gray-500">
                <th className="px-6 py-3 font-medium">Email</th>
                <th className="px-6 py-3 font-medium">Role</th>
                <th className="px-6 py-3 font-medium">Documents</th>
                <th className="px-6 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users?.map((user) => (
                <tr
                  key={user.id}
                  className="border-b border-gray-50 text-sm hover:bg-gray-50"
                >
                  <td className="px-6 py-3 text-gray-900">{user.email}</td>
                  <td className="px-6 py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        user.role === "admin"
                          ? "bg-purple-100 text-purple-700"
                          : "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {user.role}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-gray-600">
                    {user.document_count}
                  </td>
                  <td className="px-6 py-3">
                    {user.id !== me?.id ? (
                      <button
                        onClick={() => setConfirmUser(user)}
                        disabled={deleteMutation.isPending}
                        className="text-gray-400 hover:text-red-600 disabled:opacity-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {confirmUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-gray-900">
              Confirm Deletion
            </h3>
            <p className="mt-2 text-sm text-gray-600">
              Are you sure you want to delete{" "}
              <span className="font-medium text-gray-900">
                {confirmUser.email}
              </span>
              ? This will permanently remove the user from Clerk and all their
              documents, chats, and data.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setConfirmUser(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(confirmUser.id)}
                disabled={deleteMutation.isPending}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? "Deleting..." : "Delete User"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
