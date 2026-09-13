import { formatDateShort } from "@/lib/format";

const SEVERITY_META: Record<string, { label: string; dot: string; border: string }> = {
  red: { label: "Action required", dot: "bg-terracotta", border: "border-l-terracotta" },
  amber: { label: "Opportunity", dot: "bg-bronze", border: "border-l-bronze" },
  green: { label: "Strong opportunity", dot: "bg-sage", border: "border-l-sage" },
};

export interface RecommendationCard {
  id?: number;
  severity: string;
  category?: string;
  observation: string;
  interpretation?: string;
  action: string;
  expected_impact: string;
  confidence: string;
  target_start_date?: string | null;
  target_end_date?: string | null;
}

/** "Today's Intelligence" card — see docs/ARCHITECTURE.md section 7/8. The
 * OBSERVATION -> ACTION -> IMPACT structure is deterministic, produced by
 * the recommendation engine; nothing here is invented at render time. */
export default function ActionCard({
  rec,
  onDismiss,
  onAction,
}: {
  rec: RecommendationCard;
  onDismiss?: () => void;
  onAction?: () => void;
}) {
  const meta = SEVERITY_META[rec.severity] || SEVERITY_META.amber;
  const dateRange =
    rec.target_start_date && rec.target_end_date
      ? `${formatDateShort(rec.target_start_date)} – ${formatDateShort(rec.target_end_date)}`
      : null;

  return (
    <div className={`bg-warmwhite border border-taupedark/50 border-l-[3px] ${meta.border} rounded-xl px-6 py-5`}>
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className={`severity-dot ${meta.dot}`} />
            <span className="text-[10.5px] uppercase tracking-wide text-muted">{meta.label}</span>
            {rec.category && <span className="text-[10.5px] text-muted/70">· {rec.category}</span>}
          </div>
          {dateRange && <div className="font-serif text-lg text-ink">{dateRange}</div>}
        </div>
        <span className="text-[10px] uppercase tracking-wide text-muted/80 border border-taupedark/60 rounded-full px-2.5 py-1 shrink-0">
          {rec.confidence} confidence
        </span>
      </div>

      <p className="text-[13.5px] leading-relaxed text-charcoal">{rec.observation}</p>
      {rec.interpretation && <p className="text-[13.5px] text-muted mt-1.5 leading-relaxed">{rec.interpretation}</p>}

      <div className="mt-4 bg-cream rounded-lg px-4 py-3">
        <div className="text-[10px] uppercase tracking-wide text-bronze mb-1">Recommended action</div>
        <p className="text-[13.5px] text-charcoal">{rec.action}</p>
      </div>

      <p className="text-xs text-muted mt-3">
        <span className="uppercase tracking-wide text-[10.5px]">Estimated impact</span> — {rec.expected_impact}
      </p>

      {(onDismiss || onAction) && (
        <div className="flex gap-2.5 mt-4">
          {onAction && (
            <button onClick={onAction} className="text-xs px-3.5 py-1.5 rounded-full bg-charcoal text-warmwhite hover:bg-ink">
              Mark as actioned
            </button>
          )}
          {onDismiss && (
            <button onClick={onDismiss} className="text-xs px-3.5 py-1.5 rounded-full border border-taupedark hover:bg-taupe">
              Dismiss
            </button>
          )}
        </div>
      )}
    </div>
  );
}
