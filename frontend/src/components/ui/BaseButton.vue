<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, type RouteLocationRaw } from "vue-router";
import AppIcon from "./AppIcon.vue";
import type { IconName } from "./icons";

/**
 * primary = sun (only ONE per screen – the most important action)
 * secondary = navy outline · ghost = text-like · danger = destructive/negative
 * Pass `to` to render a RouterLink styled as a button (never nest <button> inside <a>).
 */
const props = withDefaults(
  defineProps<{
    variant?: "primary" | "secondary" | "ghost" | "danger";
    size?: "sm" | "md" | "lg";
    type?: "button" | "submit";
    icon?: IconName;
    loading?: boolean;
    disabled?: boolean;
    to?: RouteLocationRaw;
  }>(),
  { variant: "primary", size: "md", type: "button" },
);

const VARIANTS = {
  primary: "bg-sun text-sun-on hover:bg-sun-hover",
  secondary: "border border-line bg-surface text-fg hover:border-fg/40",
  ghost: "text-fg hover:bg-mist",
  danger: "bg-negative text-white hover:bg-negative/90",
};
const SIZES = {
  sm: "px-3 py-1.5 text-[0.82rem] gap-1.5",
  md: "px-4 py-2 text-sm gap-2",
  lg: "px-6 py-3 text-base gap-2.5", // big touch target – owner-facing decisions
};

const classes = computed(() => [VARIANTS[props.variant], SIZES[props.size]]);
</script>

<template>
  <component
    :is="to ? RouterLink : 'button'"
    :to="to"
    :type="to ? undefined : type"
    :disabled="to ? undefined : disabled || loading"
    :aria-busy="loading || undefined"
    :class="[
      'inline-flex items-center justify-center whitespace-nowrap rounded-lg font-semibold transition-colors',
      'disabled:cursor-not-allowed disabled:opacity-50',
      classes,
    ]"
  >
    <AppIcon v-if="loading" name="loader" :size="size === 'lg' ? 18 : 15" class="animate-spin" />
    <AppIcon v-else-if="icon" :name="icon" :size="size === 'lg' ? 18 : 15" />
    <slot />
  </component>
</template>
