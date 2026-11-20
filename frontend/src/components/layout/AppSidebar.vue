<script setup lang="ts">
import { storeToRefs } from "pinia";
import AnimatedNumber from "@/components/ui/AnimatedNumber.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { t } from "@/i18n";
import { useDashboardStore } from "@/stores/dashboard";
import AppLogo from "./AppLogo.vue";
import NavLinks from "./NavLinks.vue";

/** Navy column: logo, navigation, "Saved by Avida" card pinned to the bottom (the amount glides up after approvals). */
const { kpis } = storeToRefs(useDashboardStore());
</script>

<template>
  <aside class="sticky top-0 hidden h-screen w-[232px] shrink-0 flex-col gap-7 bg-side px-3 py-5 lg:flex">
    <div class="px-2"><AppLogo /></div>
    <NavLinks orientation="vertical" />
    <div class="flex-1" />
    <div class="grid gap-3 rounded-xl border border-white/10 bg-white/5 p-3.5">
      <div class="flex items-center gap-3">
        <!-- on-navy tile (IconTile tones are for light surfaces): same 40px sm size -->
        <span class="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-mint/15 text-mint" aria-hidden="true">
          <AppIcon name="piggyBank" :size="18" />
        </span>
        <span class="grid min-w-0 gap-0.5 leading-tight">
          <span class="text-label font-semibold text-white/90">{{ t("Saved by Avida") }}</span>
          <span class="text-caption text-white/75">{{ t("next 12 months") }}</span>
        </span>
      </div>
      <AnimatedNumber :value="kpis?.saved_liquidity ?? 0" class="font-display text-2xl font-bold text-mint" />
    </div>
  </aside>
</template>
