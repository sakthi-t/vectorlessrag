import { UserProfile } from "@clerk/clerk-react";

export function ProfilePage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h2 className="mb-6 text-2xl font-bold text-gray-900">Profile</h2>
      <UserProfile />
    </div>
  );
}
