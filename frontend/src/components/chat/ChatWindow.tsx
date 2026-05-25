import { useSession } from "../../hooks/useChat";
import { MessageBubble } from "./MessageBubble";
import { LoadingSpinner } from "../common/LoadingSpinner";

interface Props {
  sessionId: string;
}

export function ChatWindow({ sessionId }: Props) {
  const { data: session, isLoading } = useSession(sessionId);

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (!session) {
    return (
      <div className="flex flex-1 items-center justify-center text-gray-400">
        <p className="text-sm">Session not found.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {session.messages && session.messages.length > 0 ? (
        session.messages
          .filter((msg) => msg.role === "user" || msg.role === "assistant")
          .map((msg) => (
            <MessageBubble
              key={msg.id}
              role={msg.role as "user" | "assistant"}
              content={msg.content}
              citations={msg.citations}
              fromCache={msg.from_cache}
            />
          ))
      ) : (
        <p className="text-center text-sm text-gray-400">
          Chat session ready. Send a message to start.
        </p>
      )}
    </div>
  );
}
