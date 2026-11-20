<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import type { IconName } from "@/components/ui/icons";
import AppLogo from "./AppLogo.vue";

/** Page footer: brand + the three honesty notes as icon chips (visible on mobile too, unlike the sidebar). */
const NOTES: { icon: IconName; text: string }[] = [
  { icon: "simulated", text: "Every action is simulated" },
  { icon: "scale", text: "Not legal advice" },
  { icon: "sparkles", text: "Open-source AI on Red Hat OpenShift AI" },
];
</script>

<template>
  <footer class="mt-auto border-t border-line">
    <div class="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-5 sm:px-6">
      <AppLogo :on-dark="false" :size="28" />
      <ul class="flex flex-wrap gap-x-5 gap-y-2 text-[0.8rem] text-muted">
        <li v-for="n in NOTES" :key="n.text" class="flex items-center gap-1.5">
          <AppIcon :name="n.icon" :size="14" />
          {{ n.text }}
        </li>
      </ul>
    </div>
  </footer>
</template>
