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

/**
 * One after another: results an agent delivers together (e.g. what Avida read from a new contract) appear in reading
 * order instead of all at once. Item `i` of `n` starts a little after the one before it; the whole cascade fits in
 * ~0.9 s however many items there are. Use with `class="animate-rise"`. Reduced motion drops the delays (main.css).
 */
export function stagger(i: number, n: number): { animationDelay: string } {
  const step = Math.min(70, 900 / Math.max(1, n));
  return { animationDelay: `${Math.round(i * step)}ms` };
}
