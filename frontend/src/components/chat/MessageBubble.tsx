import { Bot } from "lucide-react";
import type { CitationItem } from "../../types";

interface Props {
  role: "user" | "assistant";
  content: string;
  citations?: CitationItem[];
  fromCache?: boolean;
}

function formatCitation(c: CitationItem): string {
  return `Page ${c.page_number}`;
}

export function MessageBubble({ role, content, citations, fromCache }: Props) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`flex max-w-[70%] gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
        {!isUser && (
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gray-700">
            <Bot className="h-4 w-4 text-white" />
          </div>
        )}
        <div>
          <div
            className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
              isUser
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-900"
            }`}
          >
            {content}
          </div>
          {!isUser && fromCache && (
            <div className="mt-1 text-xs text-gray-400">
              (cached response)
            </div>
          )}
          {!isUser && citations && citations.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {citations.map((cite, i) => (
                <span
                  key={i}
                  className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700"
                >
                  {formatCitation(cite)}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
