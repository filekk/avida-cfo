<script setup lang="ts">
import AppLogo from "./AppLogo.vue";
import NavLinks from "./NavLinks.vue";
import SavingsCard from "./SavingsCard.vue";

/** Navy column: logo, navigation, "Saved by Avida" card with its small savings chart pinned to the bottom. */
</script>

<template>
  <aside class="sticky top-0 hidden h-screen w-[232px] shrink-0 flex-col gap-7 overflow-y-auto bg-side px-3 py-5 lg:flex">
    <div class="px-2"><AppLogo /></div>
    <NavLinks orientation="vertical" />
    <div class="flex-1" />
    <SavingsCard />
  </aside>
</template>
