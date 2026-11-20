<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import type { IconName } from "@/components/ui/icons";
import { useWheelchairEgg } from "@/composables/useWheelchairEgg";
import { t } from "@/i18n";
import AppLogo from "./AppLogo.vue";

/** Page footer: brand + the three honesty notes as icon chips (visible on mobile too, unlike the sidebar). */
const NOTES: { icon: IconName; text: string; egg?: boolean }[] = [
  { icon: "simulated", text: "Every action is simulated" },
  { icon: "scale", text: "Not legal advice" },
  { icon: "sparkles", text: "Open-source AI on Red Hat OpenShift AI", egg: true },
];

/**
 * Hidden on purpose (composables/useWheelchairEgg): five quick clicks/taps on the last note swap the accessibility
 * icon. No role, no tab stop, no cursor – it looks like plain text. select-none: rapid clicks don't highlight it;
 * touch-manipulation: a quick double tap doesn't zoom on phones; no grey tap flash on iOS.
 */
const { tap } = useWheelchairEgg();
const EGG_EVENTS = { click: tap };
const EGG_CLASS = "select-none touch-manipulation [-webkit-tap-highlight-color:transparent]";
</script>

<template>
  <footer class="mt-auto border-t border-line">
    <div class="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-5 sm:px-6">
      <AppLogo :on-dark="false" :size="30" />
      <ul class="flex flex-wrap gap-x-5 gap-y-2 text-label text-muted">
        <li v-for="n in NOTES" :key="n.text" :class="['flex items-center gap-1.5', n.egg && EGG_CLASS]" v-on="n.egg ? EGG_EVENTS : {}">
          <AppIcon :name="n.icon" :size="16" />
          {{ t(n.text) }}
        </li>
      </ul>
    </div>
  </footer>
</template>
