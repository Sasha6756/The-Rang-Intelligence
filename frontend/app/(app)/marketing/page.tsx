"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";

export default function MarketingPage() {
  const [mining, setMining] = useState<any[]>([]);
  const [channelMix, setChannelMix] = useState<any[]>([]);

  useEffect(() => {
    apiGet("/api/recommendations/review-mining").then(setMining);
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 90);
    apiGet(`/api/analytics/channel-mix?start=${start.toISOString().slice(0, 10)}&end=${end.toISOString().slice(0, 10)}`).then(setChannelMix);
  }, []);

  const directShare = channelMix.find((c) => c.channel === "Direct")?.revenue_share_pct;

  return (
    <div>
      <h1 className="font-serif text-3xl text-ink mb-1">Marketing</h1>
      <p className="text-muted text-sm mb-8 max-w-2xl">
        Full marketing-content-to-revenue attribution (campaign tracking, ROI by channel) is on the roadmap — the
        schema has room for it (see the campaigns table) but it isn't wired up to a real ad platform yet. What's
        already real: direct-booking share, and review themes worth featuring in your own content.
      </p>

      {directShare !== undefined && (
        <div className="bg-warmwhite border border-taupedark/50 rounded-2xl p-6 mb-8 max-w-md">
          <div className="text-[10.5px] uppercase tracking-wide text-muted mb-2">Direct booking share, last 90 days</div>
          <div className="font-serif text-4xl text-ink tnum">{directShare}%</div>
          <p className="text-xs text-muted mt-2">Share of revenue from Direct vs OTA channels — the lever marketing content and repeat-guest campaigns can move.</p>
        </div>
      )}

      <h3 className="text-sm font-medium text-ink mb-3">Content candidates from guest reviews</h3>
      {mining.length === 0 ? (
        <p className="text-muted text-sm">No recurring review themes surfaced yet — import reviews from Experience.</p>
      ) : (
        <div className="grid sm:grid-cols-2 gap-3 mb-10">
          {mining.map((m) => (
            <div key={m.phrase} className="bg-bronze/8 border border-bronze/25 rounded-2xl px-5 py-4">
              <div className="text-sm capitalize text-charcoal">"{m.phrase}"</div>
              <div className="text-xs text-muted mt-1">Mentioned in {m.share_of_reviews}% of reviews ({m.mentions} mentions).</div>
            </div>
          ))}
        </div>
      )}

      <div className="bg-taupe/40 border border-taupedark/40 rounded-2xl p-6 text-sm text-muted max-w-2xl">
        <span className="text-charcoal font-medium">Coming in a later phase:</span> campaign tracking, marketing
        spend ROI by channel, and Instagram/GA4 integration once those connections are built.
      </div>
    </div>
  );
}
