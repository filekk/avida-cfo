import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { prefersReducedMotion } from "@/utils/motion";

declare module "vue-router" {
  interface RouteMeta {
    /** Shown in the topbar and the browser tab. */
    title?: string;
    /** Shell to render the page in (default "app"). See App.vue. */
    layout?: "app" | "blank";
  }
}

// History mode works in production because FastAPI serves index.html for every unknown path (main.py → spa()).
// Views are lazy-loaded → one chunk per page.
const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "dashboard",
    component: () => import("@/views/DashboardView.vue"),
    meta: { title: "Your money at a glance" },
  },
  // Findings were merged into the Action center. Old links (e.g. from the overview) still work:
  // /findings/:id opens the Action center with that finding expanded.
  { path: "/findings", name: "findings", redirect: { name: "decisions" } },
  {
    path: "/findings/:id",
    name: "finding-detail",
    redirect: (to) => ({ name: "decisions", query: { finding: String(to.params.id) } }),
  },
  {
    path: "/decisions",
    name: "decisions",
    component: () => import("@/views/DecisionsView.vue"),
    meta: { title: "Action center" },
  },
  // "Ask your CFO" has no page: it is the floating chat on the overview and a contextual panel in each decision.
  // Old /ask links land in the Action center.
  { path: "/ask", name: "ask", redirect: { name: "decisions" } },
  {
    path: "/contracts",
    name: "contracts",
    component: () => import("@/views/ContractsView.vue"),
    meta: { title: "Your contracts" },
  },
  // "Agent permissions" page removed: every autonomy badge explains itself in a tooltip. Old links → overview.
  { path: "/policy", name: "policy", redirect: { name: "dashboard" } },
  {
    path: "/history",
    name: "history",
    component: () => import("@/views/HistoryView.vue"),
    meta: { title: "History" },
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: () => import("@/views/NotFoundView.vue"),
    meta: { title: "Page not found" },
  },
];

/** Sticky top bar height + some air, so a #hash target doesn't end up underneath it. */
function topBarOffset(): number {
  return (document.querySelector<HTMLElement>("header.sticky")?.offsetHeight ?? 0) + 16;
}

/**
 * Waits until the #hash target exists AND stops moving: the view is lazy, the page transition (out-in + a small
 * rise) runs first, and the store data above the target may still arrive. Gives up after `timeout` ms.
 */
async function settledTarget(id: string, timeout = 2500): Promise<HTMLElement | null> {
  const start = performance.now();
  let el: HTMLElement | null = null;
  let lastTop = Number.NaN;
  let still = 0;
  while (performance.now() - start < timeout) {
    await new Promise((resolve) => requestAnimationFrame(resolve));
    el = document.getElementById(id);
    if (!el) continue;
    const top = el.getBoundingClientRect().top + window.scrollY;
    still = Math.abs(top - lastTop) < 1 ? still + 1 : 0;
    lastTop = top;
    if (still >= 6) return el; // ~100 ms without moving
  }
  return el;
}

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  async scrollBehavior(to, _from, saved) {
    if (saved) return saved;
    if (to.hash) {
      const el = await settledTarget(decodeURIComponent(to.hash.slice(1)));
      if (el) return { el, top: topBarOffset(), behavior: prefersReducedMotion() ? "auto" : "smooth" };
    }
    return { top: 0 };
  },
});

// document.title is set in App.vue (follows the page AND the chosen language).
