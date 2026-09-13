/** A restrained, generative visual mark for the property banner — not a
 * stock photo, and not a fabricated photograph claiming to be "The Rang"
 * (this app doesn't have real property photography to draw on). A quiet
 * architectural silhouette in the house palette reads as premium without
 * pretending to be something it isn't. */
export default function PropertyHero({ name, address }: { name: string; address: string }) {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-ink mb-8">
      <svg viewBox="0 0 1200 260" className="absolute inset-0 w-full h-full opacity-[0.55]" preserveAspectRatio="xMidYMax slice">
        <defs>
          <linearGradient id="skyline" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2A2521" />
            <stop offset="100%" stopColor="#161310" />
          </linearGradient>
        </defs>
        <rect width="1200" height="260" fill="url(#skyline)" />
        {/* modern Balinese roofline silhouette, repeated + offset */}
        {[0, 1, 2, 3].map((i) => (
          <path
            key={i}
            d={`M${i * 340 - 60},220 L${i * 340 + 60},130 L${i * 340 + 180},130 L${i * 340 + 300},220 Z`}
            fill="none"
            stroke="#A3814F"
            strokeOpacity={0.35 - i * 0.05}
            strokeWidth={1.2}
          />
        ))}
        <line x1="0" y1="220" x2="1200" y2="220" stroke="#A3814F" strokeOpacity="0.3" strokeWidth="1" />
        {/* still water reflection lines */}
        {[228, 236, 244].map((y, i) => (
          <line key={y} x1="0" y1={y} x2="1200" y2={y} stroke="#DDD2BC" strokeOpacity={0.08 - i * 0.02} strokeWidth="1" />
        ))}
      </svg>
      <div className="relative px-6 md:px-10 py-9 md:py-12">
        <div className="text-[10px] tracking-widest2 text-bronze/90 uppercase mb-2">The Rang</div>
        <h1 className="font-serif text-4xl md:text-5xl text-warmwhite leading-none mb-2">Uluwatu, Bali</h1>
        <p className="text-taupedark/80 text-sm">{name} · {address}</p>
      </div>
    </div>
  );
}
