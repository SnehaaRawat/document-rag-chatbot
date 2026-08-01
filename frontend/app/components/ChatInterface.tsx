"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ChatMessage } from "../lib/types";

interface Props {
  messages: ChatMessage[];
  onSend: (message: string) => Promise<void>;
  sending: boolean;
  disabled: boolean;
  disabledReason?: string;
}

export default function ChatInterface({ messages, onSend, sending, disabled, disabledReason }: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending || disabled) return;
    setInput("");
    await onSend(trimmed);
  };

  return (
    <section className="flex h-full w-full flex-col bg-paper">
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {messages.length === 0 && (
          <div className="mx-auto max-w-md pt-16 text-center">
            <p className="font-serif text-lg text-ink">Ask something about your documents.</p>
            <p className="mt-2 text-sm text-inkfaint">
              Answers are grounded in the passages retrieved for each question — if nothing relevant is
              found, you'll be told plainly instead of getting a guess.
            </p>
          </div>
        )}

        <div className="mx-auto flex max-w-2xl flex-col gap-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-lg px-4 py-2.5 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "bg-moss text-paper"
                    : "border border-rule bg-paperdim font-serif text-ink"
                }`}
              >
                <p className="whitespace-pre-wrap">{m.content}</p>
                {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                  <p className="mt-1.5 border-t border-rule/60 pt-1.5 font-sans text-[11px] text-inkfaint">
                    Grounded in {m.sources.length} source{m.sources.length > 1 ? "s" : ""} — see panel →
                  </p>
                )}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="rounded-lg border border-rule bg-paperdim px-4 py-2.5 text-sm text-inkfaint">
                Retrieving and answering…
              </div>
            </div>
          )}
        </div>
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="border-t border-rule px-6 py-4">
        <div className="mx-auto flex max-w-2xl items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder={disabled ? disabledReason || "Upload a document to start" : "Ask a question about your documents…"}
            disabled={disabled}
            rows={1}
            className="max-h-32 flex-1 resize-none rounded-md border border-rule bg-paper px-3 py-2 text-sm text-ink placeholder:text-inkfaint focus:border-moss disabled:cursor-not-allowed disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={disabled || sending || !input.trim()}
            className="rounded-md bg-moss px-4 py-2 text-sm font-medium text-paper transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </form>
    </section>
  );
}
