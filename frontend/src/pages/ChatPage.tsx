import { useChatSessions, useCreateSession, useDeleteSession } from "../hooks/useChat";
import { useDocuments } from "../hooks/useDocuments";
import { useSession } from "../hooks/useChat";
import { ChatInput } from "../components/chat/ChatInput";
import { ChatWindow } from "../components/chat/ChatWindow";
import { EvaluationPanel } from "../components/chat/EvaluationPanel";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useState, useMemo } from "react";
import { MessageSquare, Plus, Trash2, BarChart3 } from "lucide-react";

export function ChatPage() {
  const { data: sessions, isLoading: sessionsLoading } = useChatSessions();
  const { data: documents } = useDocuments();
  const createSession = useCreateSession();
  const deleteSession = useDeleteSession();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [newChatOpen, setNewChatOpen] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [evalOpen, setEvalOpen] = useState(false);

  const { data: activeSession } = useSession(activeSessionId ?? "");

  const evaluationEntries = useMemo(() => {
    if (!activeSession?.messages) return [];
    return activeSession.messages
      .filter((m) => m.role === "assistant" && m.evaluation)
      .map((m) => ({
        id: m.id,
        content: m.content,
        evaluation: m.evaluation!,
      }));
  }, [activeSession]);

  const readyDocs = documents?.filter((d) => d.status === "ready") ?? [];

  const handleNewChat = () => {
    if (!selectedDocId && readyDocs.length > 0) return;
    createSession.mutate(
      { documentId: selectedDocId || undefined, title: "New Chat" },
      {
        onSuccess: (session) => {
          setActiveSessionId(session.id);
          setNewChatOpen(false);
        },
      }
    );
  };

  if (sessionsLoading) return <LoadingSpinner />;

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-6">
      {/* Sessions sidebar */}
      <div className="w-72 flex-shrink-0 rounded-xl border border-gray-200 bg-white p-4">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Chat Sessions</h3>
          <button
            onClick={() => setNewChatOpen(true)}
            className="rounded-lg bg-blue-600 p-1.5 text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>

        {newChatOpen && (
          <div className="mb-4 rounded-lg bg-gray-50 p-3">
            <select
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="mb-2 w-full rounded-md border border-gray-300 p-2 text-sm"
            >
              <option value="">Select a document...</option>
              {readyDocs.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                </option>
              ))}
            </select>
            <button
              onClick={handleNewChat}
              disabled={!selectedDocId}
              className="w-full rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Start Chat
            </button>
          </div>
        )}

        <div className="space-y-1">
          {sessions?.length === 0 && (
            <p className="text-sm text-gray-400">No chat sessions yet.</p>
          )}
          {sessions?.map((session) => (
            <button
              key={session.id}
              onClick={() => setActiveSessionId(session.id)}
              className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                activeSessionId === session.id
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-700 hover:bg-gray-50"
              }`}
            >
              <MessageSquare className="h-4 w-4 flex-shrink-0" />
              <span className="flex-1 truncate">{session.title || "Untitled"}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteSession.mutate(session.id);
                }}
                className="text-gray-400 hover:text-red-500"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </button>
          ))}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex flex-1 flex-col rounded-xl border border-gray-200 bg-white">
        {activeSessionId ? (
          <>
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-2">
              <span className="text-sm font-medium text-gray-600">Chat</span>
              <button
                onClick={() => setEvalOpen(!evalOpen)}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                  evalOpen
                    ? "bg-blue-100 text-blue-700"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                <BarChart3 className="h-3.5 w-3.5" />
                {evalOpen ? "Hide Evaluation" : "Show Evaluation"}
              </button>
            </div>
            <div className="flex flex-1 overflow-hidden">
              <div className="flex flex-1 flex-col">
                <ChatWindow sessionId={activeSessionId} />
                <ChatInput sessionId={activeSessionId} />
              </div>
              <EvaluationPanel
                evaluations={evaluationEntries}
                isOpen={evalOpen}
                onToggle={() => setEvalOpen(!evalOpen)}
              />
            </div>
          </>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center text-gray-400">
            <MessageSquare className="mb-3 h-12 w-12" />
            <p className="text-sm">Select a chat session or start a new one.</p>
          </div>
        )}
      </div>
    </div>
  );
}
