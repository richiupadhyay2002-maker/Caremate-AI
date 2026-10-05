import { cn } from "@/lib/utils";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Optional header content rendered above the body */
  header?: React.ReactNode;
  /** Optional footer content rendered below the body */
  footer?: React.ReactNode;
}

/**
 * Clinical card — white surface, 1px hairline border (#DCE3E0),
 * 10px radius, NO drop shadow. Flat and calm.
 */
export function Card({ className, header, footer, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "bg-clinical-surface border border-clinical-border rounded-[10px]",
        "flex flex-col",
        className,
      )}
      {...props}
    >
      {header && (
        <div className="px-6 py-4 border-b border-clinical-border">{header}</div>
      )}
      <div className="px-6 py-5 flex-1">{children}</div>
      {footer && (
        <div className="px-6 py-4 border-t border-clinical-border bg-clinical-surface">
          {footer}
        </div>
      )}
    </div>
  );
}
