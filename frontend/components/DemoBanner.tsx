export default function DemoBanner({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <div className="bg-bronze/10 border border-bronze/30 text-bronzedark text-xs px-4 py-2 rounded-lg mb-6 tracking-wide">
      DEMO DATA — fictional bookings, reviews and competitor rates generated to show how the platform works. Import
      your own data from Settings to replace it.
    </div>
  );
}
