<script setup lang="ts">
import { computed, nextTick, ref, useId } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import type { IconName } from "@/components/ui/icons";
import { TEXT_SIZES, useA11y, type Contrast } from "@/composables/useA11y";
import { usePopover } from "@/composables/usePopover";
import { useTheme, type ThemeChoice } from "@/composables/useTheme";
import { useWheelchairEgg } from "@/composables/useWheelchairEgg";
import { t } from "@/i18n";
import { pct } from "@/utils/format";
import A11yFigure from "./A11yFigure.vue";

/**
 * Accessibility settings, top-right on every page. Open/close behaviour is the shared top-bar pop-up
 * (composables/usePopover): hover opens for mouse users, click/tap/Enter/Space pins it, Escape / click outside /
 * focus leaving closes. Keyboard users land on the current text size, so the arrow keys change it right away.
 * English text lives in the option arrays and is translated where it is rendered.
 */
const { prefs, reduceMotion, isDefault, setReduceMotion, reset } = useA11y();
const { choice: theme, set: setTheme } = useTheme();

const panel = ref<HTMLElement | null>(null);
const { open, root, trigger, close, onPointerEnter, onPointerLeave, onTriggerClick, onFocusOut } = usePopover({
  hover: true,
  onKeyboardOpen: () => nextTick(() => panel.value?.querySelector<HTMLElement>("input:checked")?.focus()),
});
const panelId = `a11y-panel-${useId()}`;

// --- trigger icon -------------------------------------------------------------------------------
// Standing figure by default; the footer easter egg (useWheelchairEgg) swaps in the wheelchair figure, which rolls
// and waves while a mouse/pen hovers the trigger (touch has no hover). Both icons share one grid cell and cross-fade.
const { wheelchair } = useWheelchairEgg();
const hovered = ref(false);
const ICON_SWAP = "col-start-1 row-start-1 transition-[opacity,transform] duration-slow ease-out";
const ICON_HIDDEN = "scale-50 opacity-0";

// --- options (English; translated in the template) ----------------------------------------------
const textIndex = computed(() => TEXT_SIZES.findIndex((s) => s.value === prefs.text));
const textPct = computed(() => TEXT_SIZES[textIndex.value]?.pct ?? 100);
/** The four "A" get bigger left → right (em, so they follow the current size too). */
const A_SIZE = ["0.8em", "0.95em", "1.1em", "1.3em"];

/** `swatch` = a tiny preview of the scheme, so the choice is obvious without reading. */
const CONTRASTS: { value: Contrast; label: string; swatch: string }[] = [
  { value: "standard", label: "Standard", swatch: "bg-white text-[#0E2A47] ring-1 ring-[#0E2A47]/25" },
  { value: "high", label: "Yellow on black", swatch: "bg-[#000] text-[#FFFF00] ring-1 ring-[#FFFF00]" },
];
const contrastIndex = computed(() => CONTRASTS.findIndex((c) => c.value === prefs.contrast));

const THEMES: { value: ThemeChoice; label: string; icon: IconName }[] = [
  { value: "light", label: "Light", icon: "sun" },
  { value: "dark", label: "Dark", icon: "moon" },
  { value: "system", label: "Auto", icon: "monitor" },
];
const themeIndex = computed(() => THEMES.findIndex((o) => o.value === theme.value));

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

function resetAll() {
  reset();
  setTheme("system");
}

/** Sliding indicator under the chosen option of a segmented control. */
const indicator = (index: number, count: number) => ({
  width: `calc((100% - 0.5rem) / ${count})`,
  transform: `translateX(${Math.max(0, index) * 100}%)`,
});

const SEGMENT =
  "relative z-10 flex min-h-11 cursor-pointer items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-center text-label font-semibold leading-tight " +
  "has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px] has-[:focus-visible]:outline-offset-1 has-[:focus-visible]:outline-sun";
const INDICATOR = "absolute inset-y-1 left-1 rounded-lg bg-sun transition-transform duration-base ease-out";
</script>

<template>
  <div ref="root" class="relative" @pointerenter="onPointerEnter" @pointerleave="onPointerLeave" @focusout="onFocusOut">
    <button
      ref="trigger"
      type="button"
      :class="[
        'grid h-10 w-10 place-items-center rounded-lg border text-fg',
        open ? 'border-fg/40 bg-mist' : 'border-line bg-surface hover:bg-mist',
      ]"
      :aria-label="t('Accessibility settings')"
      :title="t('Accessibility settings')"
      :aria-expanded="open"
      :aria-controls="panelId"
      @click="onTriggerClick"
      @pointerenter="hovered = $event.pointerType !== 'touch'"
      @pointerleave="hovered = false"
    >
      <AppIcon name="personStanding" :size="20" :class="[ICON_SWAP, wheelchair && `${ICON_HIDDEN} -rotate-45`]" />
      <A11yFigure :size="20" :moving="wheelchair && hovered" :class="[ICON_SWAP, !wheelchair && `${ICON_HIDDEN} rotate-45`]" />
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
        :aria-label="t('Accessibility settings')"
        class="absolute right-0 top-full z-30 mt-2 grid max-h-[calc(100dvh-5.5rem)] w-[22rem] max-w-[calc(100vw-2rem)] origin-top-right gap-4 overflow-y-auto overscroll-contain rounded-xl border border-line bg-surface p-4 text-fg shadow-pop"
      >
        <!-- header -->
        <div class="flex items-start justify-between gap-3">
          <div class="grid gap-0.5">
            <h2 class="text-base font-semibold">{{ t("Make Avida easier to use") }}</h2>
            <p class="text-label text-muted">{{ t("Saved on this device.") }}</p>
          </div>
          <button
            type="button"
            class="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-muted hover:bg-mist hover:text-fg"
            :aria-label="t('Close accessibility settings')"
            @click="close(true)"
          >
            <AppIcon name="x" :size="18" />
          </button>
        </div>

        <!-- text size -->
        <div class="grid gap-2">
          <div class="flex items-center justify-between gap-2">
            <span :id="`${panelId}-text`" class="flex items-center gap-2 text-label font-semibold">
              <AppIcon name="textSize" :size="18" class="text-muted" /> {{ t("Text size") }}
            </span>
            <span class="rounded-md bg-input px-2 py-0.5 text-caption font-medium tabular-nums text-muted">{{ pct(textPct, false) }}</span>
          </div>
          <div role="radiogroup" :aria-labelledby="`${panelId}-text`" class="relative grid grid-cols-4 rounded-xl bg-input p-1">
            <span :class="INDICATOR" :style="indicator(textIndex, TEXT_SIZES.length)" aria-hidden="true" />
            <label
              v-for="(s, i) in TEXT_SIZES"
              :key="s.value"
              :class="[SEGMENT, prefs.text === s.value ? 'text-sun-on' : 'text-muted hover:text-fg']"
            >
              <input v-model="prefs.text" type="radio" class="sr-only" :name="`${panelId}-text`" :value="s.value" :aria-label="t(s.label)" />
              <span class="font-display font-semibold leading-none" :style="{ fontSize: A_SIZE[i] }" aria-hidden="true">A</span>
            </label>
          </div>
        </div>

        <!-- contrast -->
        <div class="grid gap-2">
          <span :id="`${panelId}-contrast`" class="flex items-center gap-2 text-label font-semibold">
            <AppIcon name="contrast" :size="18" class="text-muted" /> {{ t("Contrast") }}
          </span>
          <div role="radiogroup" :aria-labelledby="`${panelId}-contrast`" class="relative grid grid-cols-2 rounded-xl bg-input p-1">
            <span :class="INDICATOR" :style="indicator(contrastIndex, CONTRASTS.length)" aria-hidden="true" />
            <label
              v-for="c in CONTRASTS"
              :key="c.value"
              :class="[SEGMENT, prefs.contrast === c.value ? 'text-sun-on' : 'text-muted hover:text-fg']"
            >
              <input v-model="prefs.contrast" type="radio" class="sr-only" :name="`${panelId}-contrast`" :value="c.value" />
              <!-- fixed preview colours on purpose: it shows what the scheme looks like -->
              <span :class="['grid h-6 w-7 shrink-0 place-items-center rounded font-display text-caption font-semibold', c.swatch]" aria-hidden="true">Aa</span>
              {{ t(c.label) }}
            </label>
          </div>
        </div>

        <!-- theme -->
        <div class="grid gap-2">
          <span :id="`${panelId}-theme`" class="flex items-center gap-2 text-label font-semibold">
            <AppIcon name="eye" :size="18" class="text-muted" /> {{ t("Colours") }}
          </span>
          <div role="radiogroup" :aria-labelledby="`${panelId}-theme`" class="relative grid grid-cols-3 rounded-xl bg-input p-1">
            <span :class="INDICATOR" :style="indicator(themeIndex, THEMES.length)" aria-hidden="true" />
            <label
              v-for="o in THEMES"
              :key="o.value"
              :class="[SEGMENT, theme === o.value ? 'text-sun-on' : 'text-muted hover:text-fg']"
            >
              <input
                type="radio"
                class="sr-only"
                :name="`${panelId}-theme`"
                :value="o.value"
                :checked="theme === o.value"
                @change="setTheme(o.value)"
              />
              <AppIcon :name="o.icon" :size="16" />{{ t(o.label) }}
            </label>
          </div>
          <p v-if="prefs.contrast === 'high'" class="flex items-start gap-1.5 text-caption text-muted">
            <AppIcon name="info" :size="14" class="mt-0.5" /> {{ t("Yellow on black is used while high contrast is on.") }}
          </p>
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
                <span class="text-label font-semibold">{{ t(s.label) }}</span>
                <span class="text-caption text-muted">{{ t(s.hint) }}</span>
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
          @click="resetAll"
        >
          <AppIcon name="reset" :size="16" /> {{ t("Reset to default") }}
        </button>
      </section>
    </Transition>
  </div>
</template>
