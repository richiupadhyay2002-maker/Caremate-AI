import { cn } from "@/lib/utils";

export type StatusType = "safe" | "review" | "urgent" | "pending";

const statusConfig: Record<StatusType, { label: string; className: string }> = {
  safe: {
    label: "Safe",
    className: "text-status-safe bg-status-safe-bg",
  },
  review: {
    label: "Needs review",
    className: "text-status-review bg-status-review-bg",
  },
  urgent: {
    label: "Urgent",
    className: "text-status-urgent bg-status-urgent-bg",
  },
  pending: {
    label: "Pending review",
    className: "text-ink-secondary bg-clinical-border/20",
  },
};

export interface StatusBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement> {
  status: StatusType;
  label?: string;
  dot?: boolean;
}

/**
 * Small pill-shaped status badge with colored text on a tinted
 * background (never a solid saturated fill).
 */
export function StatusBadge({
  status,
  label,
  dot = false,
  className,
  ...props
}: StatusBadgeProps) {
  const cfg = statusConfig[status] ?? statusConfig.pending;
  const displayLabel = label ?? cfg.label;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
        cfg.className,
        className,
      )}
      {...props}
    >
      {dot && (
        <span
          className={cn(
            "w-1.5 h-1.5 rounded-full",
            status === "safe" && "bg-status-safe",
            status === "review" && "bg-status-review",
            status === "urgent" && "bg-status-urgent",
            status === "pending" && "bg-ink-secondary",
          )}
        />
      )}
      {displayLabel}
    </span>
  );
}
