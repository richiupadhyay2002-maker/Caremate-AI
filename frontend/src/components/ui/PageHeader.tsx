import { cn } from "@/lib/utils";

export interface PageHeaderProps extends React.HTMLAttributes<HTMLElement> {
  /** Small muted eyebrow label shown above the H1 */
  eyebrow?: string;
  /** The main page title */
  title: string;
  /** Optional action elements (buttons, etc.) */
  action?: React.ReactNode;
}

/**
 * Page header pattern:
 *  - small muted eyebrow (portal name)
 *  - large serif H1
 */
export function PageHeader({
  eyebrow,
  title,
  action,
  className,
  ...props
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        "flex items-baseline justify-between mb-6",
        className,
      )}
      {...props}
    >
      <div>
        {eyebrow && (
          <p className="text-xs font-medium text-ink-secondary uppercase tracking-wider">
            {eyebrow}
          </p>
        )}
        <h1 className="text-3xl font-heading text-ink-primary mt-1">
          {title}
        </h1>
      </div>
      {action}
    </header>
  );
}
