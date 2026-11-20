import { onBeforeUnmount, ref, watch, type Ref } from "vue";
import { prefersReducedMotion as reducedMotion } from "@/utils/motion";

/**
 * A number that glides to its new value (ease-out) instead of jumping – e.g. "Saved by Avida" going up
 * after an approval. First value appears instantly; respects reduced motion.
 */
export function useTweenedNumber(source: Ref<number>, duration = 700): Ref<number> {
  const shown = ref(source.value);
  let frame = 0;

  watch(source, (to) => {
    cancelAnimationFrame(frame);
    const from = shown.value;
    if (from === to || reducedMotion()) {
      shown.value = to;
      return;
    }
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      shown.value = from + (to - from) * eased;
      if (t < 1) frame = requestAnimationFrame(step);
      else shown.value = to;
    };
    frame = requestAnimationFrame(step);
  });

  onBeforeUnmount(() => cancelAnimationFrame(frame));
  return shown;
}
