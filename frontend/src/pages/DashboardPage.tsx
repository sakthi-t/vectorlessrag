import { useDocuments, useUploadDocument } from "../hooks/useDocuments";
import { DocumentsPage } from "./DocumentsPage";
import { UploadModal } from "../components/documents/UploadModal";
import { useState } from "react";
import { Upload } from "lucide-react";

export function DashboardPage() {
  const { data: documents } = useDocuments();
  const uploadMutation = useUploadDocument();
  const [uploadOpen, setUploadOpen] = useState(false);

  const readyCount = documents?.filter((d) => d.status === "ready").length ?? 0;
  const totalCount = documents?.length ?? 0;

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
          <p className="mt-1 text-sm text-gray-500">Manage your documents and chats</p>
        </div>
        <button
          onClick={() => setUploadOpen(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 shadow-sm"
        >
          <Upload className="h-4 w-4" />
          Upload PDF
        </button>
      </div>

      <div className="mb-8 grid gap-6 sm:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-medium text-gray-500">Total Documents</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">{totalCount}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-medium text-gray-500">Ready to Chat</p>
          <p className="mt-2 text-3xl font-bold text-green-600">{readyCount}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-medium text-gray-500">Processing</p>
          <p className="mt-2 text-3xl font-bold text-yellow-600">
            {totalCount - readyCount}
          </p>
        </div>
      </div>

      <div>
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Your Documents</h3>
        <DocumentsPage />
      </div>

      <UploadModal
        isOpen={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUpload={(file) => uploadMutation.mutate(file)}
        uploading={uploadMutation.isPending}
      />
    </div>
  );
}
