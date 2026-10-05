import { cn } from "@/lib/utils";
import Link from "next/link";

export type ButtonVariant = "primary" | "secondary" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  asChild?: boolean;
  href?: string;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-teal text-white hover:bg-brand-teal-hover focus:ring-2 focus:ring-brand-teal/30",
  secondary:
    "border border-clinical-border text-ink-primary hover:bg-clinical-border/10 focus:ring-2 focus:ring-ink-secondary/20",
  ghost:
    "text-ink-secondary hover:bg-clinical-border/10 focus:ring-2 focus:ring-ink-secondary/20",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-2.5 text-base",
};

/**
 * Clinical buttons:
 * - Primary: solid brand-teal, white text, 8px radius.
 * - Secondary / ghost: outline-only, no fill.
 */
export function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  disabled,
  href,
  asChild = false,
  ...props
}: ButtonProps) {
  const classes = cn(
    "inline-flex items-center justify-center rounded-[8px] font-medium",
    "transition-colors duration-150",
    "disabled:opacity-50 disabled:cursor-not-allowed",
    variantStyles[variant],
    sizeStyles[size],
    className,
  );

  if (href) {
    return (
      <Link href={href} className={classes}>
        {children}
      </Link>
    );
  }

  if (asChild) {
    return (
      <span className={classes} {...props}>
        {children}
      </span>
    );
  }

  return (
    <button className={classes} disabled={disabled} {...props}>
      {children}
    </button>
  );
}
