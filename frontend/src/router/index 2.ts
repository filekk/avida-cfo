import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

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
  {
    path: "/policy",
    name: "policy",
    component: () => import("@/views/PolicyView.vue"),
    meta: { title: "What your agents may do" },
  },
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

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
});

// document.title is set in App.vue (follows the page AND the chosen language).
