<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import SafetyRing from "./SafetyRing.vue";

/** One sentence the owner understands at a glance (backend `headline`) + the "days safe" ring. */
defineProps<{ headline: string; safe: boolean; daysSafe: number; horizon: number }>();
</script>

<template>
  <section class="relative isolate flex items-center gap-5 overflow-hidden rounded-2xl bg-side px-5 py-5 text-white sm:gap-6 sm:px-7 sm:py-6">
    <span :class="['absolute inset-y-0 left-0 w-1.5', safe ? 'bg-mint' : 'bg-sun']" aria-hidden="true" />
    <!-- soft glow, decoration only -->
    <span
      :class="['pointer-events-none absolute -right-20 -top-24 -z-10 h-64 w-64 rounded-full blur-3xl', safe ? 'bg-mint/15' : 'bg-sun/15']"
      aria-hidden="true"
    />
    <SafetyRing :days="daysSafe" :horizon="horizon" :safe="safe" />
    <div class="grid min-w-0 gap-2">
      <span class="eyebrow flex items-center gap-1.5 !text-side-fg">
        <AppIcon :name="safe ? 'checkCircle' : 'alert'" :size="14" :class="safe ? 'text-mint' : 'text-sun'" />
        {{ safe ? "You're on track" : "Heads-up" }}
      </span>
      <p class="max-w-3xl font-display text-base font-bold leading-snug sm:text-xl">{{ headline }}</p>
    </div>
  </section>
</template>
