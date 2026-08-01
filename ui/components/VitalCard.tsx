import { LucideIcon } from "lucide-react";

interface VitalCardProps {
  icon: LucideIcon;
  label: string;
  value: string;
  subvalue?: string;
  alert?: boolean;
  color?: "accent" | "danger" | "warning" | "info";
}

const COLOR_MAP: Record<string, string> = {
  accent: "text-accent",
  danger: "text-danger",
  warning: "text-warning",
  info: "text-info",
};

export default function VitalCard({ icon: Icon, label, value, subvalue, alert, color = "accent" }: VitalCardProps) {
  return (
    <div className={`card p-4 flex flex-col gap-1 ${alert ? "border-danger pulse-danger" : ""}`}>
      <div className="flex items-center gap-2 text-gray-400 text-xs uppercase tracking-wide">
        <Icon size={14} />
        {label}
      </div>
      <div className={`text-2xl font-bold ${COLOR_MAP[color]}`}>{value}</div>
      {subvalue && <div className="text-xs text-gray-500">{subvalue}</div>}
    </div>
  );
}
