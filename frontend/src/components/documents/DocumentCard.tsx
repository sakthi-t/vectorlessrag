import type { Document } from "../../types";

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  processing: "bg-blue-100 text-blue-800",
  ready: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

interface Props {
  document: Document;
  onDelete: (id: string) => void;
}

export function DocumentCard({ document, onDelete }: Props) {
  const sizeMB = (document.file_size_bytes / (1024 * 1024)).toFixed(2);

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50 text-red-600">
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H8V4h12v12zM4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm12 6V9c0-.55-.45-1-1-1h-2v5h2c.55 0 1-.45 1-1zm-2-3h1v3h-1V9zm4 2h1v-1h-1V9h1V8h-2v5h1v-2zm-8 0h1v-1H9v-1h1V8H9v.5H8v1h1v.5H8v1h1V12z" />
            </svg>
          </div>
          <div>
            <h3 className="font-medium text-gray-900 text-sm truncate max-w-[200px]">
              {document.filename}
            </h3>
            <p className="text-xs text-gray-500">{sizeMB} MB</p>
          </div>
        </div>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${statusColors[document.status] || "bg-gray-100 text-gray-800"}`}
        >
          {document.status}
        </span>
      </div>
      <div className="mt-4 flex justify-end">
        <button
          onClick={() => onDelete(document.id)}
          className="rounded-lg px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
