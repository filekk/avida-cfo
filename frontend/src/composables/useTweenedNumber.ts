import { onBeforeUnmount, onMounted, ref, watch, type Ref } from "vue";
import { prefersReducedMotion as reducedMotion } from "@/utils/motion";

export interface TweenOptions {
  /** ms for a change of value (e.g. "Saved by Avida" going up after an approval) */
  duration?: number;
  /** the first value counts up from 0 when the number appears, instead of standing there at once */
  countUp?: boolean;
}

/** Count-up on first show: quick, then settles – reads as "the numbers just came in", not as a slot machine. */
const COUNT_UP_MS = 900;
/** ease-out quart: most of the way in the first third, a soft landing */
const ease = (p: number) => 1 - Math.pow(1 - p, 4);

/**
 * A number that glides to its new value instead of jumping. With `countUp` it also counts up from 0 when it
 * first appears. Respects reduced motion (OS setting + accessibility menu): then it simply shows the value.
 */
export function useTweenedNumber(source: Ref<number>, { duration = 700, countUp = false }: TweenOptions = {}): Ref<number> {
  const shown = ref(countUp && !reducedMotion() ? 0 : source.value);
  let frame = 0;

  function glide(to: number, ms: number) {
    cancelAnimationFrame(frame);
    const from = shown.value;
    if (from === to || reducedMotion()) {
      shown.value = to;
      return;
    }
    const start = performance.now();
    const step = (now: number) => {
      const p = Math.min(1, (now - start) / ms);
      shown.value = from + (to - from) * ease(p);
      if (p < 1) frame = requestAnimationFrame(step);
      else shown.value = to;
    };
    frame = requestAnimationFrame(step);
  }

  watch(source, (to) => glide(to, duration));
  onMounted(() => glide(source.value, COUNT_UP_MS));
  onBeforeUnmount(() => cancelAnimationFrame(frame));
  return shown;
}
