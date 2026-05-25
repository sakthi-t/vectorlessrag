import { useState } from "react";
import { useSendMessage } from "../../hooks/useChat";
import { Send } from "lucide-react";

interface Props {
  sessionId: string;
}

export function ChatInput({ sessionId }: Props) {
  const [input, setInput] = useState("");
  const sendMessage = useSendMessage();

  const handleSend = () => {
    if (!input.trim()) return;
    sendMessage.mutate({ sessionId, content: input.trim() });
    setInput("");
  };

  return (
    <div className="border-t border-gray-200 p-4">
      <div className="flex items-center gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about your document..."
          className="flex-1 rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || sendMessage.isPending}
          className="rounded-xl bg-blue-600 p-3 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
