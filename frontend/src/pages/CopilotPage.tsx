import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Bot, Send, User, ShieldCheck, Wrench, AlertTriangle, Sparkles, ChevronDown } from "lucide-react";
import { postChatMessage, getAiToolsManifest } from "../services/analyticsApi";
import { toApiError, type ApiError } from "../services/apiClient";
import { useApiData } from "../hooks/useApiData";
import type { ChatResponse } from "../types/api";

interface DisplayMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  meta?: ChatResponse;
  error?: ApiError;
}

const SUGGESTED_PROMPTS = [
  "Why did our costs spike?",
  "What are our biggest optimization opportunities?",
  "What is our carbon footprint?",
  "What will our cloud cost look like over the next 30 days?",
  "Which resources are underutilized?",
];

function newId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function CopilotPage() {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const toolsManifest = useApiData(getAiToolsManifest, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;

    const userMessage: DisplayMessage = { id: newId(), role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSending(true);

    try {
      // Send prior turns as conversation_history so the model has context,
      // using only the fields the ChatRequest schema actually defines.
      const conversationHistory = messages.map((m) => ({
        role: (m.role === "assistant" ? "model" : "user") as "user" | "model",
        content: m.content,
      }));

      const response = await postChatMessage({
        message: trimmed,
        conversation_history: conversationHistory,
      });

      setMessages((prev) => [
        ...prev,
        { id: newId(), role: "assistant", content: response.answer, meta: response },
      ]);
    } catch (err) {
      const apiError = toApiError(err);
      setMessages((prev) => [
        ...prev,
        {
          id: newId(),
          role: "assistant",
          content:
            "I couldn't reach the CloudSense AI Copilot backend for this question.",
          error: apiError,
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-6.5rem)] lg:h-[calc(100vh-7rem)]">
      <div ref={scrollRef} className="flex-1 overflow-y-auto pr-1 flex flex-col gap-4 pb-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center flex-1 gap-4 py-10 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-500/15 text-brand-400">
              <Bot size={24} />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-ink">CloudSense AI FinOps Copilot</h2>
              <p className="text-xs text-ink-faint mt-1 max-w-sm">
                Ask a question about cost, usage, anomalies, optimization, carbon, or forecasts.
                Every answer is grounded in the verified analytics backend — nothing here is guessed.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 max-w-lg">
              {SUGGESTED_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => sendMessage(p)}
                  className="rounded-full border border-surface-border bg-surface-raised px-3 py-1.5 text-xs text-ink-muted hover:text-ink hover:border-brand-500/50 transition-colors"
                >
                  {p}
                </button>
              ))}
            </div>

            {toolsManifest.data && toolsManifest.data.tools.length > 0 && (
              <details className="w-full max-w-lg text-left group">
                <summary className="cursor-pointer list-none flex items-center justify-center gap-1.5 text-xs text-ink-faint hover:text-ink-muted transition-colors">
                  <ChevronDown size={13} className="transition-transform group-open:rotate-180" />
                  What can the Copilot actually check? ({toolsManifest.data.tools.length} tools)
                </summary>
                <ul className="mt-3 flex flex-col gap-1.5 rounded-lg border border-surface-border bg-surface-raised p-3">
                  {toolsManifest.data.tools.map((tool) => (
                    <li key={tool.name} className="text-xs">
                      <span className="font-mono text-brand-400">{tool.name}</span>
                      <span className="text-ink-faint"> — {tool.description}</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}

        {messages.map((m) => (
          <ChatBubble key={m.id} message={m} />
        ))}

        {sending && (
          <div className="flex items-start gap-2.5">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-500/15 text-brand-400">
              <Bot size={15} />
            </div>
            <div className="card px-3.5 py-2.5 text-sm text-ink-faint">
              <span className="inline-flex gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-ink-faint animate-bounce [animation-delay:-0.3s]" />
                <span className="h-1.5 w-1.5 rounded-full bg-ink-faint animate-bounce [animation-delay:-0.15s]" />
                <span className="h-1.5 w-1.5 rounded-full bg-ink-faint animate-bounce" />
              </span>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex items-end gap-2 border-t border-surface-border pt-3">
        <label htmlFor="copilot-input" className="sr-only">
          Ask the FinOps Copilot a question
        </label>
        <textarea
          id="copilot-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendMessage(input);
            }
          }}
          placeholder="Ask about cost, usage, anomalies, optimization, carbon, or forecasts…"
          rows={1}
          className="flex-1 resize-none rounded-lg bg-surface-raised border border-surface-border px-3 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-1 focus:ring-brand-500 max-h-32"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          aria-label="Send message"
          className="flex items-center justify-center rounded-lg bg-brand-500 hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed text-white h-10 w-10 shrink-0 transition-colors"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}

function ChatBubble({ message }: { message: DisplayMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex items-start gap-2.5 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
          isUser ? "bg-surface-raised text-ink-muted" : "bg-brand-500/15 text-brand-400"
        }`}
      >
        {isUser ? <User size={14} /> : <Bot size={15} />}
      </div>

      <div className={`flex flex-col gap-2 max-w-[85%] sm:max-w-[75%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-xl2 px-3.5 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "bg-brand-500 text-white"
              : message.error
              ? "card border-severity-critical/40 text-ink"
              : "card text-ink"
          }`}
        >
          {message.error ? (
            <div className="flex items-start gap-2">
              <AlertTriangle size={15} className="text-severity-critical mt-0.5 shrink-0" />
              <span>{message.error.message}</span>
            </div>
          ) : isUser ? (
            <span>{message.content}</span>
          ) : (
            <div className="prose-chat">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {message.meta && !message.error && <GroundingFooter meta={message.meta} />}
      </div>
    </div>
  );
}

function GroundingFooter({ meta }: { meta: ChatResponse }) {
  const hasMetrics = Object.keys(meta.relevant_metrics ?? {}).length > 0;

  return (
    <div className="flex flex-col gap-1.5 w-full text-xs text-ink-faint">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`pill ${
            meta.is_grounded
              ? "bg-positive/15 text-positive border border-positive/30"
              : "bg-severity-medium/15 text-severity-medium border border-severity-medium/30"
          }`}
        >
          <ShieldCheck size={12} />
          {meta.is_grounded ? "Grounded in analytics" : "Not grounded"}
        </span>

        {meta.tools_used.length > 0 && (
          <span className="pill bg-surface-raised text-ink-muted border border-surface-border">
            <Wrench size={12} />
            {meta.tools_used.join(", ")}
          </span>
        )}
      </div>

      {meta.warnings.length > 0 && (
        <div className="flex items-start gap-1.5 text-severity-medium">
          <AlertTriangle size={12} className="mt-0.5 shrink-0" />
          <span>{meta.warnings.join(" ")}</span>
        </div>
      )}

      {meta.analytical_sources.length > 0 && (
        <span className="text-ink-faint">
          Sources: {meta.analytical_sources.join(", ")}
        </span>
      )}

      {hasMetrics && (
        <details className="group">
          <summary className="cursor-pointer text-ink-faint hover:text-ink-muted inline-flex items-center gap-1 list-none">
            <Sparkles size={12} />
            View underlying metrics
          </summary>
          <pre className="mt-1.5 rounded-lg border border-surface-border bg-surface-raised p-2.5 text-[11px] text-ink-muted overflow-x-auto">
            {JSON.stringify(meta.relevant_metrics, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
