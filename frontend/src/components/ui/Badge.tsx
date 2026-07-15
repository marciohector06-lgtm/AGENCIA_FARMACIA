const colorMap: Record<string, string> = {
  slate: "bg-slate-500/10 text-slate-700 ring-1 ring-inset ring-slate-500/20",
  green: "bg-emerald-500/10 text-emerald-700 ring-1 ring-inset ring-emerald-500/25",
  red: "bg-red-500/10 text-red-700 ring-1 ring-inset ring-red-500/25",
  yellow: "bg-amber-500/10 text-amber-700 ring-1 ring-inset ring-amber-500/25",
  blue: "bg-blue-500/10 text-blue-700 ring-1 ring-inset ring-blue-500/25",
};

export function Badge({ children, color = "slate" }: { children: React.ReactNode; color?: keyof typeof colorMap }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colorMap[color]}`}>
      {children}
    </span>
  );
}
