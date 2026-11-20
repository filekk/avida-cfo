<script setup lang="ts">
/**
 * Lucide "accessibility" (ISC, see THIRD_PARTY_LICENSES.md) as inline SVG, split into parts that can move.
 * At rest it draws the Lucide icon (same coordinates, stroke 2, currentColor); only the stroke
 * "m5 8 3-3 5.5 3-2.36 3.5" is cut at its corners into forearm / upper arm / back so the arm can move.
 * `moving` (trigger hovered): the wheel rolls, the arm lifts and the hand waves. Reduced motion → still.
 */
withDefaults(defineProps<{ moving?: boolean; size?: number }>(), { moving: false, size: 20 });
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="['shrink-0', { 'is-moving': moving }]"
    aria-hidden="true"
  >
    <!-- head, leg, back -->
    <circle cx="16" cy="4" r="1" />
    <path d="m18 19 1-7-6 1" />
    <path d="M13.5 8 11.14 11.5" />
    <!-- arm: lifts at the shoulder; the forearm waves at the elbow -->
    <g class="part arm">
      <path d="M13.5 8 8 5" />
      <g class="part hand">
        <path d="M8 5 5 8" />
      </g>
    </g>
    <!-- wheel: two arcs around (9, 16), r = 5 -->
    <g class="part wheel">
      <path d="M4.24 14.5a5 5 0 0 0 6.88 6" />
      <path d="M13.76 17.5a5 5 0 0 0-6.88-6" />
    </g>
  </svg>
</template>

<style scoped>
/* Pivot points in icon coordinates (24×24 viewBox). */
.part {
  transform-box: view-box;
}
.wheel {
  transform-origin: 9px 16px;
}
.arm {
  transform-origin: 13.5px 8px;
  transition: rotate var(--dur-slow) var(--ease-out); /* lifts and lowers smoothly */
}
.hand {
  transform-origin: 8px 5px;
}

/* Wheel: one calm turn every 1.8 s (forward = clockwise). Hand: about one wave per second; the negative
   delay starts it mid-swing (0°), so nothing jumps when the hover begins. */
.is-moving .arm {
  rotate: 20deg;
}
.is-moving .wheel {
  animation: a11y-roll 1800ms linear infinite;
}
.is-moving .hand {
  animation: a11y-wave 520ms var(--ease-in-out) -260ms infinite alternate;
}

@keyframes a11y-roll {
  to {
    rotate: 360deg;
  }
}
@keyframes a11y-wave {
  from {
    rotate: -26deg;
  }
  to {
    rotate: 26deg;
  }
}

/* Reduced motion (OS unless the menu says "full", or the menu itself): stay still. */
@media (prefers-reduced-motion: reduce) {
  :root:not([data-motion="full"]) .part {
    animation: none;
    rotate: none;
  }
}
:root[data-motion="reduce"] .part {
  animation: none;
  rotate: none;
}
</style>
