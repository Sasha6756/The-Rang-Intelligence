const SEVERITY_META: Record<string, { label: string; dot: string; border: string }> = {
  red: { label: "Action required", dot: "bg-terracotta", border: "border-l-terracotta" },
  amber: { label: "Listing opportunity", dot: "bg-bronze", border: "border-l-bronze" },
  green: { label: "Opportunity", dot: "bg-sage", border: "border-l-sage" },
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
}

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
  return (
    <div className={`bg-warmwhite border border-taupedark/50 border-l-[3px] ${meta.border} rounded-lg px-5 py-4 shadow-card`}>
      <div className="flex items-center gap-2 mb-2">
        <span className={`severity-dot ${meta.dot}`} />
        <span className="text-[11px] uppercase tracking-wide text-muted">{meta.label}</span>
        {rec.category && <span className="text-[11px] text-muted/70">· {rec.category}</span>}
        <span className="ml-auto text-[10px] uppercase tracking-wide text-muted/70 border border-taupedark/60 rounded-full px-2 py-0.5">
          {rec.confidence} confidence
        </span>
      </div>
      <p className="text-sm leading-relaxed">{rec.observation}</p>
      {rec.interpretation && <p className="text-sm text-muted mt-2 leading-relaxed">{rec.interpretation}</p>}
      <div className="mt-3 bg-taupe/50 rounded-md px-3 py-2.5">
        <div className="text-[11px] uppercase tracking-wide text-bronze mb-1">Recommendation</div>
        <p className="text-sm">{rec.action}</p>
      </div>
      <p className="text-xs text-muted mt-2">
        <span className="uppercase tracking-wide">Estimated impact:</span> {rec.expected_impact}
      </p>
      {(onDismiss || onAction) && (
        <div className="flex gap-3 mt-3">
          {onAction && (
            <button onClick={onAction} className="text-xs px-3 py-1.5 rounded-md bg-charcoal text-warmwhite hover:bg-bronzedark">
              Mark as actioned
            </button>
          )}
          {onDismiss && (
            <button onClick={onDismiss} className="text-xs px-3 py-1.5 rounded-md border border-taupedark hover:bg-taupe">
              Dismiss
            </button>
          )}
        </div>
      )}
    </div>
  );
}
