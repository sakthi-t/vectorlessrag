import apiClient from "./client";
import type { Document } from "../types";

export async function getDocuments(): Promise<Document[]> {
  const { data } = await apiClient.get("/api/v1/documents");
  return data;
}

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post("/api/v1/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getDocument(id: string): Promise<Document> {
  const { data } = await apiClient.get(`/api/v1/documents/${id}`);
  return data;
}

export async function deleteDocument(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/documents/${id}`);
}

export async function getDocumentStatus(id: string): Promise<{ id: string; status: string }> {
  const { data } = await apiClient.get(`/api/v1/documents/${id}/status`);
  return data;
}
