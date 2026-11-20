<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useDashboardStore } from "@/stores/dashboard";
import { eur } from "@/utils/format";
import AppLogo from "./AppLogo.vue";
import NavLinks from "./NavLinks.vue";

/** Prototype ".side": navy column, sun-tinted active item, info box pinned to the bottom. */
const { kpis } = storeToRefs(useDashboardStore());
</script>

<template>
  <aside class="sticky top-0 hidden h-screen w-[232px] shrink-0 flex-col gap-6 bg-side px-3 py-5 lg:flex">
    <div class="px-2"><AppLogo /></div>
    <NavLinks orientation="vertical" />
    <div class="flex-1" />
    <div class="grid gap-1.5 rounded-xl bg-white/5 p-3 text-[0.8rem] text-side-fg">
      <b class="font-display text-white">Saved by Avida</b>
      <span class="font-display text-xl font-bold tabular-nums text-mint">{{ eur(kpis?.saved_liquidity ?? 0) }}</span>
      <span>over the next 12 months</span>
    </div>
    <p class="px-2 text-[0.72rem] leading-snug text-side-fg/80">
      All actions are simulated. Contract checks are not legal advice.
    </p>
  </aside>
</template>
