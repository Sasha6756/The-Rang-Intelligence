export default function StatCard({
  label,
  value,
  sublabel,
  accent,
}: {
  label: string;
  value: string;
  sublabel?: string;
  accent?: "bronze" | "sage" | "terracotta";
}) {
  const accentColor = accent === "sage" ? "text-sage" : accent === "terracotta" ? "text-terracotta" : "text-bronze";
  return (
    <div className="bg-warmwhite border border-taupedark/50 rounded-lg px-5 py-4 shadow-card">
      <div className="text-[11px] uppercase tracking-wide text-muted mb-1.5">{label}</div>
      <div className={`font-serif text-2xl ${accentColor}`}>{value}</div>
      {sublabel && <div className="text-xs text-muted mt-1">{sublabel}</div>}
    </div>
  );
}
