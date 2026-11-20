<script setup lang="ts">
defineProps<{ label: string; value: string; sub?: string; highlight?: boolean }>();
</script>

<template>
  <div :class="['rounded-2xl p-4 shadow-sm', highlight ? 'bg-emerald-50 ring-2 ring-emerald-400' : 'bg-white']">
    <p class="text-sm text-slate-500">{{ label }}</p>
    <p class="text-2xl font-extrabold">{{ value }}</p>
    <p v-if="sub" class="text-sm text-slate-500">{{ sub }}</p>
  </div>
</template>
