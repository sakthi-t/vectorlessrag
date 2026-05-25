import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as documentsApi from "../api/documents";

export function useDocuments() {
  return useQuery({
    queryKey: ["documents"],
    queryFn: documentsApi.getDocuments,
    refetchInterval: (query) => {
      const docs = query.state.data;
      if (!docs || docs.length === 0) return false;
      const hasProcessing = docs.some(
        (d) => d.status === "pending" || d.status === "processing"
      );
      return hasProcessing ? 3000 : false;
    },
  });
}

export function useDocument(id: string) {
  return useQuery({
    queryKey: ["documents", id],
    queryFn: () => documentsApi.getDocument(id),
    enabled: !!id,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => documentsApi.uploadDocument(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => documentsApi.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useDocumentStatus(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["documents", id, "status"],
    queryFn: () => documentsApi.getDocumentStatus(id),
    refetchInterval: enabled ? 3000 : false,
    enabled,
  });
}
