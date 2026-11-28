<script setup lang="ts">
import { nextTick, onBeforeUnmount, reactive, ref, useId, watch } from "vue";

/**
 * Tooltip for small things that need a word of explanation (e.g. the autonomy badges).
 * - opens on mouse hover AND keyboard focus (the trigger gets tabindex 0), closes on leave / blur / Escape;
 *   the pointer may move onto the bubble without it closing (WCAG 1.4.13: hoverable, dismissible)
 * - rendered into <body> with fixed position → never cut off by a card with overflow-hidden or a scroll box;
 *   above the trigger, flips below when there is no room, kept 8px inside the screen edges
 * - readable for everyone: 14px text, navy bubble with white text and a light border (stands out on any card)
 * The bubble is always in the DOM (v-show), so `aria-describedby` also works for screen readers.
 * One root element (the trigger span) – the Teleport lives inside it.
 */
defineProps<{ text: string; title?: string }>();

const id = `tip-${useId()}`;
const open = ref(false);
const trigger = ref<HTMLElement | null>(null);
const tip = ref<HTMLElement | null>(null);
const pos = reactive({ top: 0, left: 0, arrow: 0, below: false });
let closeTimer: ReturnType<typeof setTimeout> | undefined;

const EDGE = 8;
const GAP = 8;

function place() {
  const t = trigger.value;
  const b = tip.value;
  if (!t || !b) return;
  const r = t.getBoundingClientRect();
  const w = b.offsetWidth;
  const h = b.offsetHeight;
  const below = r.top - h - GAP < EDGE;
  const left = Math.min(Math.max(r.left + r.width / 2 - w / 2, EDGE), window.innerWidth - w - EDGE);
  Object.assign(pos, {
    top: below ? r.bottom + GAP : r.top - h - GAP,
    left,
    arrow: Math.min(Math.max(r.left + r.width / 2 - left, 12), w - 12),
    below,
  });
}

function show() {
  clearTimeout(closeTimer);
  if (open.value) return;
  open.value = true;
  nextTick(place);
}
function hide(delay = 120) {
  clearTimeout(closeTimer);
  closeTimer = setTimeout(() => (open.value = false), delay);
}
const onKey = (e: KeyboardEvent) => {
  if (e.key === "Escape") open.value = false;
};

function listen(on: boolean) {
  if (on) {
    window.addEventListener("scroll", place, true);
    window.addEventListener("resize", place);
    window.addEventListener("keydown", onKey);
  } else {
    window.removeEventListener("scroll", place, true);
    window.removeEventListener("resize", place);
    window.removeEventListener("keydown", onKey);
  }
}
watch(open, listen);
onBeforeUnmount(() => {
  clearTimeout(closeTimer);
  listen(false);
});
</script>

<template>
  <span
    ref="trigger"
    class="inline-flex w-fit cursor-help rounded-md"
    tabindex="0"
    :aria-describedby="id"
    @pointerenter="show"
    @pointerleave="hide()"
    @focusin="show"
    @focusout="hide(0)"
  >
    <slot />
    <Teleport to="body">
      <Transition name="fade">
        <span
          v-show="open"
          :id="id"
          ref="tip"
          role="tooltip"
          class="pointer-events-auto fixed z-[70] grid max-w-[min(20rem,calc(100vw-1rem))] gap-0.5 whitespace-normal rounded-lg border border-white/20 bg-side px-3 py-2 text-left text-label font-normal leading-snug text-white shadow-pop"
          :style="{ top: `${pos.top}px`, left: `${pos.left}px` }"
          @pointerenter="show"
          @pointerleave="hide()"
        >
          <span v-if="title" class="font-semibold">{{ title }}</span>
          <span class="text-white/90">{{ text }}</span>
          <!-- arrow pointing at the trigger -->
          <span
            :class="['absolute h-2.5 w-2.5 rotate-45 border-white/20 bg-side', pos.below ? '-top-[6px] border-l border-t' : '-bottom-[6px] border-b border-r']"
            :style="{ left: `${pos.arrow - 5}px` }"
            aria-hidden="true"
          />
        </span>
      </Transition>
    </Teleport>
  </span>
</template>
