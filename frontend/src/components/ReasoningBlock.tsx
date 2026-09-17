import { useCallback, useEffect, useRef, useState } from "react";

interface ReasoningBlockProps {
  /** The reasoning tokens accumulated so far */
  reasoning: string;
  /** Whether the model is still generating (shows animated cursor) */
  active: boolean;
}

/** How close to the bottom (in px) counts as "still following along" —
 * within this, new tokens keep auto-scrolling the view; beyond it, the
 * viewer has deliberately scrolled up to reread something, so new tokens
 * must not yank them back down. */
const BOTTOM_STICK_PX = 24;

/** A scroll container that auto-scrolls to the bottom as `content` grows,
 * but only while the viewer hasn't scrolled away from the bottom. */
function useStickyScroll(content: string) {
  const ref = useRef<HTMLDivElement>(null);
  const pinnedRef = useRef(true);

  const handleScroll = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    pinnedRef.current = distanceFromBottom <= BOTTOM_STICK_PX;
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (el && pinnedRef.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [content]);

  return { ref, handleScroll };
}

/** Displays the model's chain-of-thought / reasoning tokens in real-time as
 * they stream from the SSE endpoint, with an animated cursor while the
 * model is still generating. Auto-scrolls to follow new tokens as long as
 * the viewer stays near the bottom, and can be expanded into a full-screen
 * overlay — with a smooth open/close transition — for reading back through
 * a longer trace without losing your place. */
export function ReasoningBlock({ reasoning, active }: ReasoningBlockProps) {
  const [expanded, setExpanded] = useState(false);
  const { ref: dockedRef, handleScroll: handleDockedScroll } = useStickyScroll(reasoning);
  const { ref: overlayRef, handleScroll: handleOverlayScroll } = useStickyScroll(reasoning);

  useEffect(() => {
    if (!expanded) return;
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") setExpanded(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [expanded]);

  if (!reasoning && !active) return null;

  const body = reasoning || (active ? "Thinking…" : "");

  return (
    <>
      <div className="reasoning-block">
        <div className="reasoning-header">
          <span className="reasoning-icon">🧠</span>
          <span className="reasoning-label">Reasoning</span>
          {active && (
            <span className="reasoning-dots">
              <span>.</span>
              <span>.</span>
              <span>.</span>
            </span>
          )}
          <button
            type="button"
            className="reasoning-expand-btn"
            onClick={() => setExpanded(true)}
            aria-label="Expand reasoning"
            title="Expand"
          >
            ⤢
          </button>
        </div>
        <div className="reasoning-content" ref={dockedRef} onScroll={handleDockedScroll}>
          {body}
          {active && <span className="reasoning-cursor">▊</span>}
        </div>
      </div>

      {/* Always mounted (just hidden) rather than conditionally rendered,
          so both opening and closing get the CSS transition below instead
          of one direction popping instantly. */}
      <div
        className={`reasoning-overlay${expanded ? " open" : ""}`}
        onClick={() => setExpanded(false)}
        aria-hidden={!expanded}
        inert={!expanded}
      >
        <div className="reasoning-overlay-panel" onClick={(event) => event.stopPropagation()}>
          <div className="reasoning-header">
            <span className="reasoning-icon">🧠</span>
            <span className="reasoning-label">Reasoning</span>
            {active && (
              <span className="reasoning-dots">
                <span>.</span>
                <span>.</span>
                <span>.</span>
              </span>
            )}
            <button
              type="button"
              className="reasoning-expand-btn"
              onClick={() => setExpanded(false)}
              aria-label="Collapse reasoning"
              title="Collapse"
            >
              ⤡
            </button>
          </div>
          <div
            className="reasoning-content reasoning-content-overlay"
            ref={overlayRef}
            onScroll={handleOverlayScroll}
          >
            {body}
            {active && <span className="reasoning-cursor">▊</span>}
          </div>
        </div>
      </div>
    </>
  );
}
