<script setup lang="ts">
import AnimatedNumber from "@/components/ui/AnimatedNumber.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import IconTile from "@/components/ui/IconTile.vue";
import type { IconName } from "@/components/ui/icons";
import StatusPill from "@/components/ui/StatusPill.vue";
import { TONE_TEXT, TONE_TREND } from "@/components/ui/tones";

/**
 * Prototype ".kpi" + icon tile. `tone` tells the owner at a glance whether a number is good or bad:
 * positive = green value + green tile, negative = red value + red tile, neutral = navy.
 * The amount glides to new values (e.g. "Saved by Avida" after an approval).
 */
withDefaults(
  defineProps<{
    label: string;
    amount: number;
    icon?: IconName;
    sub?: string;
    tone?: "neutral" | "positive" | "negative";
    /** coloured box under the amount; `icon` overrides the trend arrow (e.g. a clock for "waiting") */
    delta?: { text: string; tone: "positive" | "negative" | "neutral" | "warn"; icon?: IconName };
  }>(),
  { tone: "neutral" },
);
</script>

<template>
  <div class="rounded-xl border border-line bg-surface p-4 [container-type:inline-size] lg:p-5">
    <!-- container query: the CARD decides (icon beside the text only when the card itself is wide enough),
         so the layout works for any grid width and any accessibility text size -->
    <div class="flex flex-col gap-3 [@container(min-width:13rem)]:flex-row [@container(min-width:13rem)]:items-start">
      <IconTile v-if="icon" :icon="icon" :tone="tone === 'neutral' ? 'info' : tone" />
      <div class="grid min-w-0 content-start gap-1">
        <span class="text-label font-medium text-muted">{{ label }}</span>
        <AnimatedNumber :value="amount" :class="['font-display text-kpi font-semibold', TONE_TEXT[tone]]" />
        <!-- #sub: richer sub line (e.g. the period chip of "Saved by Avida") -->
        <slot name="sub"><span v-if="sub" class="text-label text-muted">{{ sub }}</span></slot>
        <StatusPill v-if="delta" :tone="delta.tone" class="mt-1">
          <AppIcon :name="delta.icon ?? TONE_TREND[delta.tone === 'warn' ? 'neutral' : delta.tone]" :size="14" class="shrink-0" />
          <Transition name="fade" mode="out-in"><span :key="delta.text">{{ delta.text }}</span></Transition>
        </StatusPill>
      </div>
    </div>
  </div>
</template>
