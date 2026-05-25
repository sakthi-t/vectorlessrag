import { BarChart3, ChevronRight, ChevronLeft } from "lucide-react";
import type { EvaluationScores } from "../../types";

function ScoreBar({ label, value }: { label: string; value: number }) {
  const color =
    value >= 80 ? "bg-green-500" : value >= 50 ? "bg-yellow-500" : "bg-red-500";

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-28 text-gray-500">{label}</span>
      <div className="flex flex-1 items-center gap-2">
        <div className="h-1.5 flex-1 rounded-full bg-gray-200">
          <div
            className="h-1.5 rounded-full transition-all"
            style={{ width: `${value}%`, backgroundColor: color === "bg-green-500" ? "#22c55e" : color === "bg-yellow-500" ? "#eab308" : "#ef4444" }}
          />
        </div>
        <span className={`w-8 text-right font-mono font-semibold ${value >= 80 ? "text-green-600" : value >= 50 ? "text-yellow-600" : "text-red-600"}`}>
          {value}
        </span>
      </div>
    </div>
  );
}

function MessageEvaluationCard({ content, scores }: { content: string; scores: EvaluationScores }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3">
      <p className="mb-2 line-clamp-2 text-xs text-gray-500">{content}</p>
      <div className="space-y-2">
        <ScoreBar label="Faithfulness" value={scores.faithfulness} />
        <ScoreBar label="Groundedness" value={scores.groundedness} />
        <ScoreBar label="Citation Accuracy" value={scores.citation_accuracy} />
        <ScoreBar label="Relevance" value={scores.relevance} />
      </div>
    </div>
  );
}

interface EvalEntry {
  id: string;
  content: string;
  evaluation: EvaluationScores;
}

interface EvaluationPanelProps {
  evaluations: EvalEntry[];
  isOpen: boolean;
  onToggle: () => void;
}

export function EvaluationPanel({ evaluations, isOpen, onToggle }: EvaluationPanelProps) {
  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="flex items-center justify-center rounded-l-lg border border-gray-200 bg-white p-1.5 hover:bg-gray-50"
      >
        <ChevronLeft className="h-4 w-4 text-gray-500" />
      </button>
    );
  }

  const avgScores =
    evaluations.length > 0
      ? {
          faithfulness: Math.round(
            evaluations.reduce((s, e) => s + e.evaluation.faithfulness, 0) / evaluations.length
          ),
          groundedness: Math.round(
            evaluations.reduce((s, e) => s + e.evaluation.groundedness, 0) / evaluations.length
          ),
          citation_accuracy: Math.round(
            evaluations.reduce((s, e) => s + e.evaluation.citation_accuracy, 0) / evaluations.length
          ),
          relevance: Math.round(
            evaluations.reduce((s, e) => s + e.evaluation.relevance, 0) / evaluations.length
          ),
        }
      : null;

  return (
    <div className="flex h-full w-72 flex-shrink-0 flex-col border-l border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-blue-600" />
          <span className="text-sm font-semibold text-gray-900">Evaluation</span>
        </div>
        <button
          onClick={onToggle}
          className="rounded p-1 text-gray-400 hover:text-gray-600"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {avgScores && (
          <div className="rounded-lg border border-gray-200 bg-blue-50/50 p-3">
            <p className="mb-2 text-xs font-semibold text-gray-600">Session Average</p>
            <div className="space-y-1.5">
              <ScoreBar label="Faithfulness" value={avgScores.faithfulness} />
              <ScoreBar label="Groundedness" value={avgScores.groundedness} />
              <ScoreBar label="Citation" value={avgScores.citation_accuracy} />
              <ScoreBar label="Relevance" value={avgScores.relevance} />
            </div>
          </div>
        )}

        {evaluations.length === 0 && (
          <div className="rounded-lg border border-gray-200 bg-white p-4 text-center">
            <BarChart3 className="mx-auto mb-2 h-6 w-6 text-gray-300" />
            <p className="text-xs text-gray-400">
              Ask a question to see evaluation scores here.
            </p>
          </div>
        )}

        {evaluations.map((entry) => (
          <MessageEvaluationCard
            key={entry.id}
            content={entry.content}
            scores={entry.evaluation}
          />
        ))}
      </div>
    </div>
  );
}
