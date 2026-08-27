import { useEffect, useRef } from "react";

interface ReasoningBlockProps {
  /** The reasoning tokens accumulated so far */
  reasoning: string;
  /** Whether the model is still generating (shows animated cursor) */
  active: boolean;
}

/** Displays the model's chain-of-thought / reasoning tokens in real-time
 * as they stream from the SSE endpoint. Collapsible, auto-scrolling, with
 * an animated cursor while the model is still generating.
 */
export function ReasoningBlock({ reasoning, active }: ReasoningBlockProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [reasoning]);

  if (!reasoning && !active) return null;

  return (
    <div className="reasoning-block">
      <div className="reasoning-header">
        <span className="reasoning-icon">🧠</span>
        <span className="reasoning-label">Reasoning</span>
        {active && <span className="reasoning-dots"><span>.</span><span>.</span><span>.</span></span>}
      </div>
      <div className="reasoning-content" ref={scrollRef}>
        {reasoning || (active ? "Thinking…" : "")}
        {active && <span className="reasoning-cursor">▊</span>}
      </div>
    </div>
  );
}