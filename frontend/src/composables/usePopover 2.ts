import { onBeforeUnmount, ref, watch } from "vue";

/** How many pop-ups are open right now – the top bar never slides away while one is open. */
export const openPopovers = ref(0);

/**
 * Shared open/close behaviour for every top-bar pop-up (accessibility, language, inbox check) – ONE behaviour
 * everywhere:
 *   - `hover: true`  → mouse hover opens, leaving closes after 200ms (forgiving gap to the panel)
 *   - click / tap / Enter / Space on the trigger → opens and "pins" (stays open when the pointer leaves);
 *     clicking the trigger again closes
 *   - Escape, a click outside or focus leaving the widget closes (focus returns to the trigger on Escape)
 * Bind on the wrapper: @pointerenter / @pointerleave / @focusout; on the trigger: @click="onTriggerClick".
 */
export function usePopover(opts: { hover?: boolean; onKeyboardOpen?: () => void } = {}) {
  const open = ref(false);
  const pinned = ref(false);
  const root = ref<HTMLElement | null>(null);
  const trigger = ref<HTMLElement | null>(null);
  let closeTimer: ReturnType<typeof setTimeout> | undefined;

  const cancelClose = () => clearTimeout(closeTimer);

  function close(returnFocus = false) {
    cancelClose();
    open.value = false;
    pinned.value = false;
    if (returnFocus) trigger.value?.focus();
  }
  function show(pin = true) {
    cancelClose();
    open.value = true;
    if (pin) pinned.value = true;
  }

  function onPointerEnter(e: PointerEvent) {
    if (!opts.hover || e.pointerType !== "mouse") return;
    show(false);
  }
  function onPointerLeave(e: PointerEvent) {
    if (!opts.hover || e.pointerType !== "mouse" || pinned.value) return;
    cancelClose();
    closeTimer = setTimeout(() => (open.value = false), 200);
  }
  function onTriggerClick(e: MouseEvent) {
    if (open.value && pinned.value) return close();
    show(true);
    if (e.detail === 0) opts.onKeyboardOpen?.(); // Enter/Space fire a click with detail 0
  }
  function onFocusOut(e: FocusEvent) {
    const next = e.relatedTarget as Node | null;
    if (open.value && next && !root.value?.contains(next)) close();
  }

  function onDocKeydown(e: KeyboardEvent) {
    if (e.key === "Escape" && open.value) close(!!root.value?.contains(document.activeElement));
  }
  function onDocPointerDown(e: PointerEvent) {
    if (!root.value?.contains(e.target as Node)) close();
  }
  function listen(on: boolean) {
    const fn = on ? document.addEventListener : document.removeEventListener;
    fn.call(document, "pointerdown", onDocPointerDown as EventListener, true);
    fn.call(document, "keydown", onDocKeydown as EventListener);
  }

  watch(open, (o, was) => {
    listen(o);
    if (o !== was) openPopovers.value += o ? 1 : -1;
  });
  onBeforeUnmount(() => {
    cancelClose();
    if (open.value) {
      listen(false);
      openPopovers.value -= 1;
    }
  });

  return { open, pinned, root, trigger, show, close, onPointerEnter, onPointerLeave, onTriggerClick, onFocusOut };
}
