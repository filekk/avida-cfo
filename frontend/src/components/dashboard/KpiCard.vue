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
    delta?: { text: string; tone: "positive" | "negative" | "neutral" };
  }>(),
  { tone: "neutral" },
);
</script>

<template>
  <div class="rounded-xl border border-line bg-surface p-4 shadow-card [container-type:inline-size] lg:p-5">
    <!-- container query: the CARD decides (icon beside the text only when the card itself is wide enough),
         so the layout works for any grid width and any accessibility text size -->
    <div class="flex flex-col gap-3 [@container(min-width:13rem)]:flex-row [@container(min-width:13rem)]:items-start">
      <IconTile v-if="icon" :icon="icon" :tone="tone === 'neutral' ? 'info' : tone" />
      <div class="grid min-w-0 content-start gap-1">
        <span class="text-label font-medium text-muted">{{ label }}</span>
        <AnimatedNumber :value="amount" :class="['font-display text-kpi font-bold', TONE_TEXT[tone]]" />
        <span v-if="sub" class="text-label text-muted">{{ sub }}</span>
        <StatusPill v-if="delta" :tone="delta.tone" class="mt-1">
          <AppIcon :name="TONE_TREND[delta.tone]" :size="14" />{{ delta.text }}
        </StatusPill>
      </div>
    </div>
  </div>
</template>
