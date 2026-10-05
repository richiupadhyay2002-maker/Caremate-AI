/**
 * Lightweight className merger — no external deps.
 * Filters out falsy values and joins with spaces.
 */
export function cn(
  ...classes: (string | undefined | null | false | number)[]
): string {
  return classes.filter(Boolean).join(" ");
}
