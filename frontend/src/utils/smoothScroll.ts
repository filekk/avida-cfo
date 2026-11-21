import Lenis, { type LenisOptions } from "lenis";
import "lenis/dist/lenis.css";
import type { Router } from "vue-router";
import { prefersReducedMotion } from "./motion";

/**
 * Smooth mouse-wheel scrolling for the whole page – Lenis (MIT, THIRD_PARTY_LICENSES.md).
 * Lenis eases the REAL window scroll. Nothing is moved with a transform, so text stays sharp while it moves,
 * the sticky top bar and fixed pop-ups keep working, and keyboard, scrollbar and touch scrolling stay native.
 *   - lerp 0.15: a wheel notch settles in about 0.4 s. Smooth, but quick enough for work (Lenis default 0.1 ≈ 0.7 s).
 *   - only the wheel/touchpad is smoothed; phones and tablets keep their own momentum (syncTouch off)
 *   - boxes with their own scroll (chat panel, top-bar pop-ups, sidebar, agent trace…) keep scrolling themselves
 *   - off when motion is reduced: the OS setting or the accessibility menu (<html data-motion>), switched live
 *   - a page change drops a glide still in progress, so the new page starts at the top
 */
const OPTIONS: LenisOptions = {
  lerp: 0.15,
  autoRaf: true,
  allowNestedScroll: true,
  stopInertiaOnNavigate: true,
  // the accessibility menu can override the OS setting both ways, so we decide ourselves (sync below)
  respectReducedMotion: false,
};

let lenis: Lenis | null = null;

function sync() {
  const smooth = !prefersReducedMotion();
  if (smooth && !lenis) lenis = new Lenis(OPTIONS);
  else if (!smooth && lenis) {
    lenis.destroy();
    lenis = null;
  }
}

export function installSmoothScroll(router: Router) {
  sync();
  new MutationObserver(sync).observe(document.documentElement, { attributes: true, attributeFilter: ["data-motion"] });
  window.matchMedia("(prefers-reduced-motion: reduce)").addEventListener("change", sync);
  // links already stop the glide (stopInertiaOnNavigate); this also covers buttons that navigate (router.push)
  router.beforeEach(() => {
    if (lenis?.isScrolling === "smooth") lenis.scrollTo(lenis.actualScroll, { immediate: true });
  });
}
