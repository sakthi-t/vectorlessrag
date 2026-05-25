import { SignOutButton, useUser } from "@clerk/clerk-react";
import { useQuery } from "@tanstack/react-query";
import {
  MessageSquare,
  FileText,
  LayoutDashboard,
  Shield,
  LogOut,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import apiClient from "../../api/client";

async function getMe(): Promise<{ id: string; email: string; role: string }> {
  const { data } = await apiClient.get("/api/v1/auth/me");
  return data;
}

export function Sidebar() {
  const { user } = useUser();
  const location = useLocation();

  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    staleTime: 60_000,
  });

  const isAdmin = me?.role === "admin";

  const links = [
    { to: "/", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/documents", icon: FileText, label: "Documents" },
    { to: "/chat", icon: MessageSquare, label: "Chat" },
  ];

  return (
    <aside className="fixed left-0 top-0 flex h-full w-64 flex-col border-r border-gray-200 bg-white">
      <div className="flex items-center gap-2 px-6 py-5 border-b border-gray-100">
        <MessageSquare className="h-6 w-6 text-blue-600" />
        <span className="text-lg font-semibold text-gray-900">
          Vectorless RAG
        </span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ to, icon: Icon, label }) => (
          <Link
            key={to}
            to={to}
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              location.pathname === to
                ? "bg-blue-50 text-blue-700"
                : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
            }`}
          >
            <Icon className="h-5 w-5" />
            {label}
          </Link>
        ))}

        {isAdmin && (
          <Link
            to="/admin"
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              location.pathname === "/admin"
                ? "bg-blue-50 text-blue-700"
                : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
            }`}
          >
            <Shield className="h-5 w-5" />
            Admin
          </Link>
        )}
      </nav>

      <div className="border-t border-gray-100 p-4">
        <Link
          to="/profile"
          className="flex items-center gap-3 rounded-lg p-2 hover:bg-gray-50 transition-colors"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-sm font-medium text-gray-600">
            {user?.firstName?.[0] ||
              user?.emailAddresses?.[0]?.emailAddress?.[0] ||
              "U"}
          </div>
          <div className="flex-1 truncate">
            <p className="text-sm font-medium text-gray-900 truncate">
              {user?.fullName || user?.emailAddresses?.[0]?.emailAddress}
            </p>
          </div>
        </Link>
        <SignOutButton>
          <button className="mt-1 flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-gray-400 hover:bg-gray-100 hover:text-gray-600">
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </SignOutButton>
      </div>
    </aside>
  );
}
