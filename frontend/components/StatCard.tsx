export default function StatCard({
  label,
  value,
  sublabel,
  accent,
}: {
  label: string;
  value: string;
  sublabel?: string;
  accent?: "bronze" | "sage" | "terracotta" | "steel";
}) {
  const accentColor =
    accent === "sage" ? "text-sage" : accent === "terracotta" ? "text-terracotta" : accent === "steel" ? "text-steel" : "text-ink";
  return (
    <div className="bg-warmwhite border border-taupedark/50 rounded-xl px-5 py-4">
      <div className="text-[10.5px] uppercase tracking-wide text-muted mb-2">{label}</div>
      <div className={`font-serif text-[26px] leading-none tnum ${accentColor}`}>{value}</div>
      {sublabel && <div className="text-xs text-muted mt-2">{sublabel}</div>}
    </div>
  );
}

/** Boxless "hero" stat — label, a large number, and a small directional
 * delta — for the dashboard hero and other places the brief asks not to
 * turn every figure into a boxed card (section 7). */
export function Stat({
  label,
  value,
  deltaLabel,
  deltaDirection,
  caption,
}: {
  label: string;
  value: string;
  deltaLabel?: string;
  deltaDirection?: "up" | "down" | "flat";
  caption?: string;
}) {
  const deltaColor =
    deltaDirection === "up" ? "text-sage" : deltaDirection === "down" ? "text-terracotta" : "text-muted";
  const arrow = deltaDirection === "up" ? "↑" : deltaDirection === "down" ? "↓" : "";
  return (
    <div>
      <div className="text-[10.5px] uppercase tracking-wide text-muted mb-2">{label}</div>
      <div className="font-serif text-[34px] md:text-[38px] leading-none text-ink tnum">{value}</div>
      {deltaLabel && (
        <div className={`text-xs mt-2.5 ${deltaColor}`}>
          {arrow} {deltaLabel}
          {caption && <span className="text-muted"> {caption}</span>}
        </div>
      )}
      {!deltaLabel && caption && <div className="text-xs text-muted mt-2.5">{caption}</div>}
    </div>
  );
}
