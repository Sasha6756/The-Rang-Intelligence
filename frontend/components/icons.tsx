/** A small set of minimal line icons — used sparingly (nav rail + a few
 * status glyphs) rather than as decoration throughout the product, per the
 * "quiet luxury" visual direction. Hand-drawn as plain SVG rather than
 * pulling in an icon-font/library dependency for a dozen glyphs. */
import type { SVGProps } from "react";

const base = {
  width: 17,
  height: 17,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function IconOverview(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M4 12 12 4l8 8" />
      <path d="M6 10.5V20h12v-9.5" />
      <path d="M10 20v-6h4v6" />
    </svg>
  );
}
export function IconCalendar(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <rect x="4" y="5.5" width="16" height="15" rx="2.5" />
      <path d="M4 10h16M8 3.5v4M16 3.5v4" />
    </svg>
  );
}
export function IconBookings(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M6 3.5h9.5L19 7v13.5H6z" />
      <path d="M15 3.5V7h4" />
      <path d="M9 12h6M9 15.5h6" />
    </svg>
  );
}
export function IconRevenue(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M4 18 9.5 11l4 3.5L20 6" />
      <path d="M14.5 6H20v5.5" />
    </svg>
  );
}
export function IconGuests(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <circle cx="9" cy="8.5" r="3" />
      <path d="M3.5 20c0-3.3 2.5-5.5 5.5-5.5s5.5 2.2 5.5 5.5" />
      <circle cx="17" cy="9" r="2.3" />
      <path d="M15.5 14.4c2.4.4 4 2.4 4 5.6" />
    </svg>
  );
}
export function IconExperience(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3.5 13.7 8l4.8.4-3.7 3.1 1.2 4.7L12 13.7 7.9 16.2l1.2-4.7-3.7-3.1L10.3 8z" />
    </svg>
  );
}
export function IconCompetitors(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="8.2" />
      <circle cx="12" cy="12" r="4.2" />
      <circle cx="12" cy="12" r="0.6" fill="currentColor" />
    </svg>
  );
}
export function IconMarketing(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M4 10.5v3l3.2.6L14 18v-6.4z" />
      <path d="M4 10.5 14 5.6v6.4" />
      <path d="M17.5 9.5c1 1 1 4 0 5" />
    </svg>
  );
}
export function IconForecast(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M4 17 9 10l4 3.5L20 6" strokeDasharray="1.5 3.2" />
      <path d="M4 17h16" />
    </svg>
  );
}
export function IconInsights(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M9 18h6M10 21h4" />
      <path d="M12 3a6 6 0 0 0-3.2 11.1c.5.3.9.9.9 1.5v.4h4.6v-.4c0-.6.4-1.2.9-1.5A6 6 0 0 0 12 3Z" />
    </svg>
  );
}
export function IconReports(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M7 3.5h7L18 8v12.5H7z" />
      <path d="M14 3.5V8h4" />
      <path d="M9.5 12.5h5M9.5 15.5h5M9.5 18h3" />
    </svg>
  );
}
export function IconSettings(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="2.8" />
      <path d="M19.4 13.5a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.9 2.9l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.9-2.9l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.6-1h-.2a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.6-1.1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.9-2.9l.1.1a1.7 1.7 0 0 0 1.9.3h.1a1.7 1.7 0 0 0 1-1.6v-.2a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.9 2.9l-.1.1a1.7 1.7 0 0 0-.3 1.9v.1a1.7 1.7 0 0 0 1.6 1h.2a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.6 1Z" />
    </svg>
  );
}
export function IconBell(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M6 10a6 6 0 1 1 12 0c0 4 1.5 5.2 1.5 5.2H4.5S6 14 6 10Z" />
      <path d="M10 18.5a2 2 0 0 0 4 0" />
    </svg>
  );
}
export function IconChevronDown(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} width={12} height={12} {...props}>
      <path d="m5 8.5 7 7 7-7" />
    </svg>
  );
}
export function IconSignOut(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M9 20H5.5a1.5 1.5 0 0 1-1.5-1.5v-13A1.5 1.5 0 0 1 5.5 4H9" />
      <path d="M15.5 16 20 12l-4.5-4" />
      <path d="M20 12H9" />
    </svg>
  );
}
