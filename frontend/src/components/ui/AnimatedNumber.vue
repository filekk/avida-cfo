<script setup lang="ts">
import { toRef } from "vue";
import { useTweenedNumber } from "@/composables/useTweenedNumber";
import { eur } from "@/utils/format";

/**
 * A number (money by default) that counts up from 0 when it appears and glides to every new value.
 * `count-up="false"` → appears at once, only changes glide (e.g. read-outs that are re-created on a mode switch).
 * Screen readers get the final value only. The final value also sits invisibly in the same grid cell, so the box
 * has its final width from the start: nothing next to it shifts while the digits run; text-align comes from the parent.
 */
const props = withDefaults(defineProps<{ value: number; format?: (n: number) => string; countUp?: boolean }>(), {
  format: eur,
  countUp: true,
});
const shown = useTweenedNumber(toRef(props, "value"), { countUp: props.countUp });
</script>

<template>
  <span class="inline-grid tabular-nums [&>*]:col-start-1 [&>*]:row-start-1">
    <span class="sr-only">{{ format(value) }}</span>
    <span class="invisible" aria-hidden="true">{{ format(value) }}</span>
    <span aria-hidden="true">{{ format(shown) }}</span>
  </span>
</template>
