<script setup lang="ts">
import { computed, watchEffect } from "vue";
import { useRoute } from "vue-router";
import { NAV_ITEMS } from "@/constants/navigation";
import { t } from "@/i18n";
import AppLayout from "@/layouts/AppLayout.vue";
import BlankLayout from "@/layouts/BlankLayout.vue";

// Layout is chosen per route via `meta.layout` (default: app shell).
const route = useRoute();
const layout = computed(() => (route.meta.layout === "blank" ? BlankLayout : AppLayout));

// Browser tab title: "Avida CFO | <page>", page = its name in the menu (short, easy to spot among tabs);
// pages outside the menu (404) use meta.title. Follows the language.
watchEffect(() => {
  const page = NAV_ITEMS.find((n) => n.to === route.name)?.label ?? route.meta.title;
  document.title = page ? `Avida CFO | ${t(page)}` : "Avida CFO";
});
</script>

<template>
  <component :is="layout">
    <!-- page change = quick fade out, soft rise in (shared "page" transition in main.css) -->
    <RouterView v-slot="{ Component, route: r }">
      <Transition name="page" mode="out-in">
        <div :key="r.path" class="grid grid-cols-[minmax(0,1fr)] content-start gap-5">
          <component :is="Component" />
        </div>
      </Transition>
    </RouterView>
  </component>
</template>
