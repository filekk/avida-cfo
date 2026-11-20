<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import type { IconName } from "@/components/ui/icons";
import { TEXT_SIZES, useA11y, type Contrast } from "@/composables/useA11y";
import { useTheme, type ThemeChoice } from "@/composables/useTheme";

/**
 * Accessibility settings, top-right on every page. Opens on hover (mouse), on click/tap (touch) and on
 * Enter/Space (keyboard). Mouse-hover opening closes again when the pointer leaves (small delay so the gap
 * to the panel is forgiving); a click "pins" it open until Escape, a click outside or the close button.
 */
const { prefs, reduceMotion, isDefault, setReduceMotion, reset } = useA11y();
const { choice: theme, set: setTheme } = useTheme();

const uid = useId();
const panelId = `a11y-panel-${uid}`;

// --- open / close -----------------------------------------------------------------------------
const open = ref(false);
const pinned = ref(false); // opened by click/tap/keyboard → stays open when the pointer leaves
const root = ref<HTMLElement | null>(null);
const trigger = ref<HTMLButtonElement | null>(null);
const panel = ref<HTMLElement | null>(null);
let closeTimer: ReturnType<typeof setTimeout> | undefined;

function cancelClose() {
  clearTimeout(closeTimer);
}
function close(returnFocus = false) {
  cancelClose();
  open.value = false;
  pinned.value = false;
  if (returnFocus) trigger.value?.focus();
}

function onPointerEnter(e: PointerEvent) {
  if (e.pointerType !== "mouse") return;
  cancelClose();
  open.value = true;
}
function onPointerLeave(e: PointerEvent) {
  if (e.pointerType !== "mouse" || pinned.value) return;
  cancelClose();
  closeTimer = setTimeout(() => (open.value = false), 200);
}

function onTriggerClick(e: MouseEvent) {
  const viaKeyboard = e.detail === 0; // Enter/Space fire a click with detail 0
  if (open.value && pinned.value) return close();
  open.value = true;
  pinned.value = true;
  // keyboard users land on the current text size (arrow keys change it right away)
  if (viaKeyboard) nextTick(() => panel.value?.querySelector<HTMLElement>("input:checked")?.focus());
}

/** Escape closes from anywhere; focus goes back to the trigger only if it was inside the menu. */
function onDocKeydown(e: KeyboardEvent) {
  if (e.key !== "Escape" || !open.value) return;
  close(!!root.value?.contains(document.activeElement));
}
function onFocusOut(e: FocusEvent) {
  const next = e.relatedTarget as Node | null;
  if (open.value && next && !root.value?.contains(next)) close();
}
function onDocPointerDown(e: PointerEvent) {
  if (!root.value?.contains(e.target as Node)) close();
}

function listen(on: boolean) {
  const fn = on ? document.addEventListener : document.removeEventListener;
  fn.call(document, "pointerdown", onDocPointerDown as EventListener, true);
  fn.call(document, "keydown", onDocKeydown as EventListener);
}
watch(open, listen);
onBeforeUnmount(() => {
  cancelClose();
  listen(false);
});

// --- options ----------------------------------------------------------------------------------
const textIndex = computed(() => TEXT_SIZES.findIndex((t) => t.value === prefs.text));
const textPct = computed(() => TEXT_SIZES[textIndex.value]?.pct ?? 100);
/** The four "A" get bigger left → right (em, so they follow the current size too). */
const A_SIZE = ["0.8em", "0.95em", "1.1em", "1.3em"];

const CONTRASTS: { value: Contrast; label: string }[] = [
  { value: "standard", label: "Standard" },
  { value: "high", label: "High" },
];
const contrastIndex = computed(() => CONTRASTS.findIndex((c) => c.value === prefs.contrast));

const THEMES: { value: ThemeChoice; label: string; icon: IconName }[] = [
  { value: "light", label: "Light", icon: "sun" },
  { value: "dark", label: "Dark", icon: "moon" },
  { value: "system", label: "Auto", icon: "monitor" },
];
const themeIndex = computed(() => THEMES.findIndex((t) => t.value === theme.value));

const switches = computed(() => [
  {
    key: "motion",
    label: "Reduce motion",
    hint: "Fewer animations",
    icon: "pause" as IconName,
    on: reduceMotion.value,
    toggle: () => setReduceMotion(!reduceMotion.value),
  },
  {
    key: "links",
    label: "Underline links",
    hint: "Easier to spot",
    icon: "link" as IconName,
    on: prefs.links,
    toggle: () => (prefs.links = !prefs.links),
  },
  {
    key: "spacing",
    label: "Easier reading",
    hint: "More space between letters and lines",
    icon: "type" as IconName,
    on: prefs.spacing,
    toggle: () => (prefs.spacing = !prefs.spacing),
  },
]);

/** Sliding indicator under the chosen option of a segmented control. */
const indicator = (index: number, count: number) => ({
  width: `calc((100% - 0.5rem) / ${count})`,
  transform: `translateX(${Math.max(0, index) * 100}%)`,
});

const SEGMENT =
  "relative z-10 flex min-h-11 cursor-pointer items-center justify-center gap-1.5 rounded-lg px-2 text-label font-semibold " +
  "has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px] has-[:focus-visible]:outline-offset-1 has-[:focus-visible]:outline-sun";
</script>

<template>
  <div
    ref="root"
    class="relative"
    @pointerenter="onPointerEnter"
    @pointerleave="onPointerLeave"
    @focusout="onFocusOut"
  >
    <button
      ref="trigger"
      type="button"
      :class="[
        'grid h-10 w-10 place-items-center rounded-lg border text-fg',
        open ? 'border-fg/40 bg-mist' : 'border-line bg-surface hover:bg-mist',
      ]"
      aria-label="Accessibility settings"
      title="Accessibility settings"
      :aria-expanded="open"
      :aria-controls="panelId"
      @click="onTriggerClick"
    >
      <AppIcon name="accessibility" :size="20" />
    </button>

    <Transition
      enter-active-class="transition duration-base ease-out"
      leave-active-class="transition duration-fast ease-out"
      enter-from-class="opacity-0 scale-95 -translate-y-1"
      leave-to-class="opacity-0 scale-95 -translate-y-1"
    >
      <section
        v-show="open"
        :id="panelId"
        ref="panel"
        role="dialog"
        aria-label="Accessibility settings"
        class="absolute right-0 top-full z-30 mt-2 grid max-h-[calc(100dvh-5.5rem)] w-[22rem] max-w-[calc(100vw-2rem)] origin-top-right gap-4 overflow-y-auto overscroll-contain rounded-2xl border border-line bg-surface p-4 text-fg shadow-float"
      >
        <!-- header -->
        <div class="flex items-start justify-between gap-3">
          <div class="grid gap-0.5">
            <h2 class="text-base font-bold">Make Avida easier to use</h2>
            <p class="text-label text-muted">Saved on this device.</p>
          </div>
          <button
            type="button"
            class="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-muted hover:bg-mist hover:text-fg"
            aria-label="Close accessibility settings"
            @click="close(true)"
          >
            <AppIcon name="x" :size="18" />
          </button>
        </div>

        <!-- text size -->
        <div class="grid gap-2">
          <div class="flex items-center justify-between gap-2">
            <span :id="`${panelId}-text`" class="flex items-center gap-2 text-label font-semibold">
              <AppIcon name="textSize" :size="18" class="text-muted" /> Text size
            </span>
            <span class="rounded-full bg-input px-2.5 py-0.5 text-caption font-semibold tabular-nums text-muted">{{ textPct }} %</span>
          </div>
          <div role="radiogroup" :aria-labelledby="`${panelId}-text`" class="relative grid grid-cols-4 rounded-xl bg-input p-1">
            <span
              class="absolute inset-y-1 left-1 rounded-lg bg-sun shadow-card transition-transform duration-base ease-out"
              :style="indicator(textIndex, TEXT_SIZES.length)"
              aria-hidden="true"
            />
            <label
              v-for="(t, i) in TEXT_SIZES"
              :key="t.value"
              :class="[SEGMENT, prefs.text === t.value ? 'text-sun-on' : 'text-muted hover:text-fg']"
            >
              <input v-model="prefs.text" type="radio" class="sr-only" :name="`${panelId}-text`" :value="t.value" :aria-label="t.label" />
              <span class="font-display font-extrabold leading-none" :style="{ fontSize: A_SIZE[i] }" aria-hidden="true">A</span>
            </label>
          </div>
        </div>

        <!-- contrast -->
        <div class="grid gap-2">
          <span :id="`${panelId}-contrast`" class="flex items-center gap-2 text-label font-semibold">
            <AppIcon name="contrast" :size="18" class="text-muted" /> Contrast
          </span>
          <div role="radiogroup" :aria-labelledby="`${panelId}-contrast`" class="relative grid grid-cols-2 rounded-xl bg-input p-1">
            <span
              class="absolute inset-y-1 left-1 rounded-lg bg-sun shadow-card transition-transform duration-base ease-out"
              :style="indicator(contrastIndex, CONTRASTS.length)"
              aria-hidden="true"
            />
            <label
              v-for="c in CONTRASTS"
              :key="c.value"
              :class="[SEGMENT, prefs.contrast === c.value ? 'text-sun-on' : 'text-muted hover:text-fg']"
            >
              <input v-model="prefs.contrast" type="radio" class="sr-only" :name="`${panelId}-contrast`" :value="c.value" />
              {{ c.label }}
            </label>
          </div>
        </div>

        <!-- theme -->
        <div class="grid gap-2">
          <span :id="`${panelId}-theme`" class="flex items-center gap-2 text-label font-semibold">
            <AppIcon name="eye" :size="18" class="text-muted" /> Colours
          </span>
          <div role="radiogroup" :aria-labelledby="`${panelId}-theme`" class="relative grid grid-cols-3 rounded-xl bg-input p-1">
            <span
              class="absolute inset-y-1 left-1 rounded-lg bg-sun shadow-card transition-transform duration-base ease-out"
              :style="indicator(themeIndex, THEMES.length)"
              aria-hidden="true"
            />
            <label
              v-for="t in THEMES"
              :key="t.value"
              :class="[SEGMENT, theme === t.value ? 'text-sun-on' : 'text-muted hover:text-fg']"
            >
              <input
                type="radio"
                class="sr-only"
                :name="`${panelId}-theme`"
                :value="t.value"
                :checked="theme === t.value"
                @change="setTheme(t.value)"
              />
              <AppIcon :name="t.icon" :size="16" />{{ t.label }}
            </label>
          </div>
        </div>

        <!-- on/off switches -->
        <ul class="grid gap-1 border-t border-line pt-3">
          <li v-for="s in switches" :key="s.key">
            <button
              type="button"
              role="switch"
              :aria-checked="s.on"
              class="flex min-h-12 w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left hover:bg-input"
              @click="s.toggle"
            >
              <AppIcon :name="s.icon" :size="18" class="text-muted" />
              <span class="grid min-w-0 flex-1 leading-tight">
                <span class="text-label font-semibold">{{ s.label }}</span>
                <span class="text-caption text-muted">{{ s.hint }}</span>
              </span>
              <!-- track + knob -->
              <span
                :class="[
                  'relative h-7 w-12 shrink-0 rounded-full ring-1 ring-inset transition-colors duration-base',
                  s.on ? 'bg-sun ring-sun' : 'bg-input ring-muted/50',
                ]"
                aria-hidden="true"
              >
                <span
                  :class="[
                    'absolute left-1 top-1 h-5 w-5 rounded-full transition-[transform,background-color] duration-base ease-out',
                    s.on ? 'translate-x-5 bg-sun-on' : 'bg-muted',
                  ]"
                />
              </span>
            </button>
          </li>
        </ul>

        <button
          type="button"
          class="flex w-full items-center justify-center gap-2 rounded-lg border border-line px-3 py-2.5 text-label font-semibold text-fg hover:border-fg/40 hover:bg-mist disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-line disabled:hover:bg-transparent"
          :disabled="isDefault && theme === 'system'"
          @click="reset(); setTheme('system')"
        >
          <AppIcon name="reset" :size="16" /> Reset to default
        </button>
      </section>
    </Transition>
  </div>
</template>
