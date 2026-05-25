import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as chatApi from "../api/chat";

export function useChatSessions() {
  return useQuery({
    queryKey: ["chat-sessions"],
    queryFn: chatApi.getSessions,
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: { documentId?: string; title?: string }) =>
      chatApi.createSession(params.documentId, params.title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });
}

export function useSession(id: string) {
  return useQuery({
    queryKey: ["chat-sessions", id],
    queryFn: () => chatApi.getSession(id),
    enabled: !!id,
  });
}

export function useSendMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, content }: { sessionId: string; content: string }) =>
      chatApi.sendMessage(sessionId, content),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions", variables.sessionId] });
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => chatApi.deleteSession(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });
}
