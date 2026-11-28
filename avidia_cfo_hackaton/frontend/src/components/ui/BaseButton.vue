<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, type RouteLocationRaw } from "vue-router";
import AppIcon from "./AppIcon.vue";
import type { IconName } from "./icons";

/**
 * primary = sun (only ONE per screen – the most important action)
 * secondary = navy outline · ghost = text-like · danger = destructive/negative
 * Pass `to` to render a RouterLink styled as a button (never nest <button> inside <a>).
 * Hover = colour only (no shadow, no lift); a tiny press-down answers the click.
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
  secondary: "border border-line bg-surface text-fg hover:border-fg/40 hover:bg-input/60",
  ghost: "text-fg hover:bg-mist",
  danger: "bg-negative text-white hover:bg-negative/90",
};
const SIZES = {
  sm: "min-h-[2.25rem] px-3 py-1.5 text-label gap-1.5",
  md: "min-h-[2.75rem] px-4 py-2 text-base gap-2",
  lg: "min-h-[3.25rem] px-6 py-3 text-base gap-2.5", // big touch target – owner-facing decisions
};
const ICON = { sm: 16, md: 18, lg: 20 };

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
      'inline-flex items-center justify-center whitespace-nowrap rounded-lg font-semibold',
      'transition-[color,background-color,border-color,transform,opacity] duration-fast active:scale-[0.98]',
      'disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100',
      classes,
    ]"
  >
    <AppIcon v-if="loading" name="loader" :size="ICON[size]" class="animate-spin" />
    <AppIcon v-else-if="icon" :name="icon" :size="ICON[size]" />
    <slot />
  </component>
</template>
