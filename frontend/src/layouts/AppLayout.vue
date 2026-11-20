<script setup lang="ts">
import { onMounted } from "vue";
import AppFooter from "@/components/layout/AppFooter.vue";
import AppSidebar from "@/components/layout/AppSidebar.vue";
import AppTopbar from "@/components/layout/AppTopbar.vue";
import { useDashboardStore } from "@/stores/dashboard";

/** Main shell (prototype "Panel aplikacji"): navy sidebar + topbar + scrollable content + footer. */
const store = useDashboardStore();
onMounted(() => store.load());
</script>

<template>
  <div class="flex min-h-screen">
    <AppSidebar />
    <div class="flex min-w-0 flex-1 flex-col">
      <AppTopbar />
      <main id="main" class="mx-auto w-full min-w-0 max-w-6xl flex-1 px-4 py-5 sm:px-6 sm:py-7">
        <slot />
      </main>
      <AppFooter />
    </div>
  </div>
</template>
