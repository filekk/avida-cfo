import { readonly, ref } from "vue";

/**
 * Hidden easter egg: five quick clicks/taps on the footer note "Open-source AI on Red Hat OpenShift AI" swap the
 * accessibility-menu icon (standing figure) for the wheelchair figure; five more swap it back.
 * "Quick" = each click within TAP_GAP_MS of the previous one (all five fit in < 2.4 s). A fast clicker manages
 * 150–300 ms; ordinary clicks or a double click never reach five. Module-level state → footer and top bar share it.
 */
const TAPS = 5;
const TAP_GAP_MS = 600;

const wheelchair = ref(false);
let streak = 0;
let lastTap = -Infinity;

function tap() {
  const now = performance.now();
  streak = now - lastTap <= TAP_GAP_MS ? streak + 1 : 1;
  lastTap = now;
  if (streak < TAPS) return;
  streak = 0;
  lastTap = -Infinity; // the next click starts a fresh streak
  wheelchair.value = !wheelchair.value;
}

export function useWheelchairEgg() {
  return { wheelchair: readonly(wheelchair), tap };
}
