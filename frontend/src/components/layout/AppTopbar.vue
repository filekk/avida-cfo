<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { storeToRefs } from "pinia";
import InboxCheck from "@/components/sync/InboxCheck.vue";
import { openPopovers } from "@/composables/usePopover";
import { t } from "@/i18n";
import { useDashboardStore } from "@/stores/dashboard";
import { fmtDate } from "@/utils/format";
import AccessibilityMenu from "./AccessibilityMenu.vue";
import AppLogo from "./AppLogo.vue";
import LanguageSwitch from "./LanguageSwitch.vue";
import NavLinks from "./NavLinks.vue";
import ThemeToggle from "./ThemeToggle.vue";

/**
 * Prototype ".topbar": page title + context line on the left; on the right the "Check my inbox" box (the main
 * action, reachable from every page) and the tools: theme · language · accessibility (always top-right).
 * On phones the theme toggle lives inside the accessibility menu (Colours) to keep the bar uncluttered.
 * Below lg the bar glides away while scrolling down and comes back on the first scroll up. It never hides while
 * a pop-up is open or something inside it has focus.
 */
const route = useRoute();
const { dashboard } = storeToRefs(useDashboardStore());
const title = computed(() => t((route.meta.title as string | undefined) ?? "Avida CFO"));

const bar = ref<HTMLElement | null>(null);
const hidden = ref(false);
const desktop = typeof window !== "undefined" ? window.matchMedia("(min-width: 1024px)") : null;
let lastY = 0;
let ticking = false;

function update() {
  ticking = false;
  const y = window.scrollY;
  const dy = y - lastY;
  if (Math.abs(dy) < 8) return; // ignore jitter
  const busy =
    openPopovers.value > 0 || !!bar.value?.contains(document.activeElement) || !!bar.value?.matches(":hover");
  hidden.value = !desktop?.matches && dy > 0 && y > (bar.value?.offsetHeight ?? 0) && !busy;
  lastY = y;
}
function onScroll() {
  if (!ticking) {
    ticking = true;
    requestAnimationFrame(update);
  }
}
const show = () => (hidden.value = false);

onMounted(() => {
  lastY = window.scrollY;
  window.addEventListener("scroll", onScroll, { passive: true });
  desktop?.addEventListener("change", show);
});
onBeforeUnmount(() => {
  window.removeEventListener("scroll", onScroll);
  desktop?.removeEventListener("change", show);
});
watch(() => route.fullPath, show);
watch(openPopovers, (n) => n > 0 && show());
</script>

<template>
  <header
    ref="bar"
    :class="[
      'sticky top-0 z-20 border-b border-line bg-bg transition-transform duration-base',
      hidden ? '-translate-y-full' : 'translate-y-0',
    ]"
    @focusin="show"
  >
    <!-- flex-wrap + rem min-width on the title: one row normally; at large text sizes on phones the tools move
         to a second row instead of squeezing the title to "Ihr Gel…" -->
    <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 px-4 py-3 sm:px-6">
      <div class="flex min-w-[min(100%,9rem)] flex-1 items-center gap-3">
        <!-- below lg the sidebar (and its logo) is hidden -->
        <AppLogo class="lg:hidden" :on-dark="false" :show-text="false" :size="36" />
        <div class="min-w-0">
          <!-- 2 lines on phones (large text sizes stay readable), 1 line from sm up -->
          <h1 class="line-clamp-2 break-words text-lg font-semibold leading-tight sm:line-clamp-1 sm:text-xl">{{ title }}</h1>
          <p v-if="dashboard" class="truncate text-label text-muted">
            {{ dashboard.company.name }} · {{ fmtDate(dashboard.today) }}
          </p>
        </div>
      </div>
      <div class="ml-auto flex shrink-0 items-center gap-2">
        <InboxCheck />
        <span class="mx-0.5 hidden h-6 w-px bg-line sm:block" aria-hidden="true" />
        <ThemeToggle class="hidden sm:grid" />
        <LanguageSwitch />
        <AccessibilityMenu />
      </div>
    </div>
    <!-- below lg the sidebar is hidden → horizontal nav -->
    <div class="px-3 pb-2 lg:hidden"><NavLinks orientation="horizontal" /></div>
  </header>
</template>
