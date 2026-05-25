import apiClient from "./client";
import type { ChatSession, ChatSessionDetail, ChatMessage } from "../types";

export async function createSession(documentId?: string, title?: string): Promise<ChatSession> {
  const { data } = await apiClient.post("/api/v1/chat/sessions", { document_id: documentId, title });
  return data;
}

export async function getSessions(): Promise<ChatSession[]> {
  const { data } = await apiClient.get("/api/v1/chat/sessions");
  return data;
}

export async function getSession(id: string): Promise<ChatSessionDetail> {
  const { data } = await apiClient.get(`/api/v1/chat/sessions/${id}`);
  return data;
}

export async function deleteSession(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/chat/sessions/${id}`);
}

export async function sendMessage(sessionId: string, content: string): Promise<ChatMessage> {
  const { data } = await apiClient.post(`/api/v1/chat/sessions/${sessionId}/messages`, { content });
  return data;
}
