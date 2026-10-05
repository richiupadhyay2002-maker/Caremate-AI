import { cn } from "@/lib/utils";

export interface TimelineItem {
  id: string;
  date: string | Date | null;
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}

export interface TimelineProps extends React.HTMLAttributes<HTMLDivElement> {
  items: TimelineItem[];
}

/**
 * Clinical timeline — vertical 2px line with small filled teal dots,
 * date in small muted text above a bold title.
 */
export function Timeline({ items, className }: TimelineProps) {
  return (
    <div className={cn("relative pl-6", className)}>
      {/* Vertical guide line */}
      <div className="absolute left-[7px] top-0 bottom-0 w-0.5 bg-clinical-border" />

      <div className="space-y-6">
        {items.map((item) => (
          <div key={item.id} className="relative">
            {/* Teal dot marker — centered on the vertical guide line (left 7px + 1px) */}
            <div className="absolute left-[-24px] top-1 w-4 h-4 bg-brand-teal rounded-full border-2 border-clinical-surface" />

            <p className="text-xs text-ink-secondary font-medium mb-1">
              {item.date
                ? new Date(item.date).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })
                : "Recent"}
            </p>
            <h3 className="text-sm font-semibold text-ink-primary mt-0.5">
              {item.title}
            </h3>
            {item.subtitle && (
              <p className="text-sm text-ink-secondary mt-0.5">
                {item.subtitle}
              </p>
            )}
            {item.children && <div className="mt-3">{item.children}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
