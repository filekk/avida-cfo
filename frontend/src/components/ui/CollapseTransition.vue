<script setup lang="ts">
/**
 * Smooth height + fade for anything that opens/closes (v-if / v-show inside).
 * Measures the real height, so content of any size animates – no max-height guessing, no jump.
 *   <CollapseTransition><div v-if="open">…</div></CollapseTransition>
 */
const TRANSITION = "height var(--dur-base) var(--ease-out), opacity var(--dur-base) var(--ease-out)";
/** Longest a transition may take (--dur-base is 250 ms) before we finish it ourselves. */
const SAFETY_MS = 600;

function animate(el: Element, from: number, to: number, done: () => void) {
  const e = el as HTMLElement;
  // Nothing can animate: same height, or not rendered at all (inside a `display: none` parent, e.g. the sidebar
  // below lg). `transitionend` would never fire → the element stayed at height 0 / was never removed.
  if (from === to || !e.getClientRects().length) {
    done();
    return;
  }
  e.style.overflow = "hidden";
  e.style.height = `${from}px`;
  e.style.opacity = from ? "1" : "0";
  void e.offsetHeight; // reflow → the browser registers the start values
  e.style.transition = TRANSITION;
  e.style.height = `${to}px`;
  e.style.opacity = to ? "1" : "0";
  let finished = false;
  const finish = () => {
    if (finished) return;
    finished = true;
    clearTimeout(timer);
    e.removeEventListener("transitionend", end);
    done();
  };
  const end = (ev: TransitionEvent) => {
    if (ev.target === e && ev.propertyName === "height") finish();
  };
  // safety net: the parent can be hidden mid-transition (window resized below lg) – then no event arrives either
  const timer = setTimeout(finish, SAFETY_MS);
  e.addEventListener("transitionend", end);
}

function cleanup(el: Element) {
  const e = el as HTMLElement;
  e.style.height = e.style.overflow = e.style.transition = e.style.opacity = "";
}

const onEnter = (el: Element, done: () => void) => animate(el, 0, (el as HTMLElement).scrollHeight, done);
const onLeave = (el: Element, done: () => void) => animate(el, (el as HTMLElement).scrollHeight, 0, done);
</script>

<template>
  <Transition :css="false" @enter="onEnter" @after-enter="cleanup" @leave="onLeave" @after-leave="cleanup">
    <slot />
  </Transition>
</template>
