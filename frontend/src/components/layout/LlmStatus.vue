<script setup lang="ts">
import { computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useSystemStore } from "@/stores/system";

/** Small "AI online" indicator – honesty about the model (fallback answers when it's down). */
const system = useSystemStore();
const { llm, config } = storeToRefs(system);
onMounted(() => {
  if (!llm.value) system.checkLlm();
  if (!config.value) system.loadConfig();
});

const state = computed(() => {
  if (!llm.value) return { label: "Checking AI…", dot: "bg-muted", title: "" };
  if (llm.value.ok) {
    const model = llm.value.models?.[0] ?? config.value?.model ?? "model";
    return { label: "AI online", dot: "bg-positive", title: `Open-weights model: ${model} on Red Hat OpenShift AI` };
  }
  return { label: "AI offline – cached answers", dot: "bg-warn", title: llm.value.reason ?? "" };
});
</script>

<template>
  <button
    type="button"
    class="flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 text-[0.78rem] font-semibold text-muted"
    :title="state.title"
    @click="system.checkLlm()"
  >
    <span :class="['h-2 w-2 rounded-full', state.dot]" aria-hidden="true" />
    {{ state.label }}
  </button>
</template>
