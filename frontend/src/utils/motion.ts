/**
 * Should JS-driven animations be skipped? The accessibility menu wins over the OS setting:
 *   <html data-motion="reduce"> → always reduce · data-motion="full" → always animate · unset → follow the OS.
 * CSS transitions follow the same rule (main.css).
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  const choice = document.documentElement.dataset.motion;
  if (choice === "reduce") return true;
  if (choice === "full") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
