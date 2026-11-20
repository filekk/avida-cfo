<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { storeToRefs } from "pinia";
import { useDashboardStore } from "@/stores/dashboard";
import { fmtDate } from "@/utils/format";
import LlmStatus from "./LlmStatus.vue";
import NavLinks from "./NavLinks.vue";
import ThemeToggle from "./ThemeToggle.vue";

/** Prototype ".topbar": page title + context line on the left, status & tools on the right. */
const route = useRoute();
const { dashboard } = storeToRefs(useDashboardStore());
const title = computed(() => (route.meta.title as string | undefined) ?? "Avida CFO");
</script>

<template>
  <header class="sticky top-0 z-20 border-b border-line bg-bg/90 backdrop-blur">
    <div class="flex flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
      <div class="min-w-0">
        <h1 class="truncate text-lg font-bold sm:text-xl">{{ title }}</h1>
        <p v-if="dashboard" class="truncate text-[0.82rem] text-muted">
          {{ dashboard.company.name }} · {{ fmtDate(dashboard.today) }} · amounts in {{ dashboard.company.currency }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <slot name="actions" />
        <LlmStatus />
        <ThemeToggle />
      </div>
    </div>
    <!-- below lg the sidebar is hidden → horizontal nav -->
    <div class="px-3 pb-2 lg:hidden"><NavLinks orientation="horizontal" /></div>
  </header>
</template>
