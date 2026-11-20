<script setup lang="ts">
import { storeToRefs } from "pinia";
import AppIcon from "@/components/ui/AppIcon.vue";
import { useDashboardStore } from "@/stores/dashboard";
import { eur } from "@/utils/format";
import AppLogo from "./AppLogo.vue";
import NavLinks from "./NavLinks.vue";

/** Navy column: logo, navigation, "Saved by Avida" card pinned to the bottom. */
const { kpis } = storeToRefs(useDashboardStore());
</script>

<template>
  <aside class="sticky top-0 hidden h-screen w-[232px] shrink-0 flex-col gap-7 bg-side px-3 py-5 lg:flex">
    <div class="px-2"><AppLogo /></div>
    <NavLinks orientation="vertical" />
    <div class="flex-1" />
    <div class="grid gap-3 rounded-xl border border-white/10 bg-white/5 p-3.5">
      <div class="flex items-center gap-2.5">
        <span class="grid h-9 w-9 place-items-center rounded-lg bg-mint/15 text-mint">
          <AppIcon name="piggyBank" :size="18" />
        </span>
        <span class="text-[0.8rem] font-semibold leading-tight text-side-fg">Saved by Avida<br />next 12 months</span>
      </div>
      <span class="font-display text-2xl font-bold tabular-nums text-mint">{{ eur(kpis?.saved_liquidity ?? 0) }}</span>
    </div>
  </aside>
</template>
