<script setup lang="ts">
import { onMounted } from "vue";
import AppSidebar from "@/components/layout/AppSidebar.vue";
import AppTopbar from "@/components/layout/AppTopbar.vue";
import { useDashboardStore } from "@/stores/dashboard";

/** Main shell (prototype "Panel aplikacji"): navy sidebar + topbar + scrollable content. */
const store = useDashboardStore();
onMounted(() => store.load());
</script>

<template>
  <div class="flex min-h-screen">
    <AppSidebar />
    <div class="flex min-w-0 flex-1 flex-col">
      <AppTopbar />
      <main id="main" class="mx-auto grid w-full max-w-6xl content-start gap-5 px-4 py-5 sm:px-6 sm:py-6">
        <slot />
      </main>
    </div>
  </div>
</template>
