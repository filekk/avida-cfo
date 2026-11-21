<script setup lang="ts">
import { toRef } from "vue";
import { useTweenedNumber } from "@/composables/useTweenedNumber";
import { eur } from "@/utils/format";

/** Renders a number that glides to new values (money by default). Screen readers get the final value only. */
const props = withDefaults(defineProps<{ value: number; format?: (n: number) => string }>(), { format: eur });
const shown = useTweenedNumber(toRef(props, "value"));
</script>

<template>
  <span class="tabular-nums" :aria-label="format(value)"><span aria-hidden="true">{{ format(shown) }}</span></span>
</template>
