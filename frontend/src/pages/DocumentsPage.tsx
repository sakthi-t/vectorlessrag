import { useDocuments, useDeleteDocument } from "../hooks/useDocuments";
import { DocumentList } from "../components/documents/DocumentList";
import { LoadingSpinner } from "../components/common/LoadingSpinner";

export function DocumentsPage() {
  const { data: documents, isLoading, error } = useDocuments();
  const deleteMutation = useDeleteDocument();

  if (isLoading) return <LoadingSpinner />;
  if (error) {
    return <p className="text-red-600">Failed to load documents.</p>;
  }

  return (
    <div>
      <DocumentList
        documents={documents ?? []}
        onDelete={(id) => deleteMutation.mutate(id)}
      />
    </div>
  );
}
