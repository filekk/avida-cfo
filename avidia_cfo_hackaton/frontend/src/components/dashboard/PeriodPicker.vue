<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { MIN_PERIOD_DAYS, PERIOD_PRESETS } from "@/composables/useForecastPeriod";
import { t } from "@/i18n";

/**
 * "How far ahead?" – Week · Month · 3 months · Year · Custom. A sun pill slides to the chosen option.
 * Custom opens a small "[45] days" field INSIDE the control (width animates), so the card header keeps its height.
 * `max` = days the backend forecast covers: longer options stay visible but disabled, with a plain
 * explanation (they light up by themselves when the backend forecasts further, e.g. FORECAST_DAYS=365).
 */
const props = defineProps<{ modelValue: number; max: number }>();
const emit = defineEmits<{ "update:modelValue": [days: number] }>();

const uid = useId();
const effective = computed(() => Math.min(props.modelValue, props.max));
const presetIndex = computed(() => PERIOD_PRESETS.findIndex((p) => p.days === effective.value && p.days <= props.max));
const customOpen = ref(presetIndex.value === -1);
watch(presetIndex, (i) => i === -1 && (customOpen.value = true));

const CUSTOM = PERIOD_PRESETS.length; // index of the "Custom" segment
const selected = computed(() => (customOpen.value || presetIndex.value === -1 ? CUSTOM : presetIndex.value));
const isDisabled = (days: number) => days > props.max;

function choose(i: number) {
  const p = PERIOD_PRESETS[i];
  if (isDisabled(p.days)) return showHint(true);
  customOpen.value = false;
  emit("update:modelValue", p.days);
}

// --- custom value ---------------------------------------------------------------------------------
const input = ref<HTMLInputElement | null>(null);
const draft = ref<string | number>(String(effective.value)); // v-model on type=number may hand back a number
watch(effective, (v) => (draft.value = String(v)));
let typeTimer = 0;

function openCustom() {
  customOpen.value = true;
  draft.value = String(effective.value);
  nextTick(() => input.value?.select());
}
function apply() {
  window.clearTimeout(typeTimer);
  const v = Math.round(Number(draft.value));
  if (!Number.isFinite(v) || String(draft.value).trim() === "") {
    draft.value = String(effective.value);
    return;
  }
  const days = Math.min(props.max, Math.max(MIN_PERIOD_DAYS, v));
  if (v > props.max) showHint(true); // explain why it stopped at the maximum
  draft.value = String(days);
  if (days !== props.modelValue) emit("update:modelValue", days);
}
function onType() {
  window.clearTimeout(typeTimer);
  typeTimer = window.setTimeout(apply, 800);
}

// --- "why is Year disabled?" hint (hover, focus or tap) --------------------------------------------
const hint = ref(false);
let hintTimer = 0;
function showHint(autoHide = false) {
  window.clearTimeout(hintTimer);
  hint.value = true;
  if (autoHide) hintTimer = window.setTimeout(() => (hint.value = false), 2600);
}
function hideHint() {
  window.clearTimeout(hintTimer);
  hint.value = false;
}

// --- sliding pill: measured from the chosen segment -------------------------------------------------
const group = ref<HTMLDivElement | null>(null);
const segments = ref<HTMLElement[]>([]);
const pill = ref({ x: 0, y: 0, w: 0, h: 0 });
const pillReady = ref(false); // first placement without animation (no slide-in from the corner)

function placePill() {
  const el = segments.value[selected.value];
  if (!el) return;
  pill.value = { x: el.offsetLeft, y: el.offsetTop, w: el.offsetWidth, h: el.offsetHeight };
}
watch([selected, () => props.max, effective], () => nextTick(placePill));

let ro: ResizeObserver | null = null;
onMounted(() => {
  placePill();
  requestAnimationFrame(() => (pillReady.value = true));
  // follows the custom field while it opens, wrapping on small screens and the a11y text size
  ro = new ResizeObserver(placePill);
  if (group.value) {
    ro.observe(group.value);
    segments.value.forEach((el) => ro?.observe(el));
  }
});
onBeforeUnmount(() => {
  ro?.disconnect();
  window.clearTimeout(typeTimer);
  window.clearTimeout(hintTimer);
});
</script>

<template>
  <div class="relative">
    <div
      ref="group"
      class="relative flex flex-wrap items-center rounded-xl border border-line bg-input p-1"
      role="group"
      :aria-label="t('Forecast period')"
    >
      <!-- sliding sun pill behind the chosen option -->
      <span
        :class="[
          'pointer-events-none absolute left-0 top-0 rounded-lg bg-sun',
          pillReady ? 'transition-[transform,width,height] duration-base' : '',
        ]"
        :style="{ transform: `translate(${pill.x}px, ${pill.y}px)`, width: `${pill.w}px`, height: `${pill.h}px` }"
        aria-hidden="true"
      />
      <button
        v-for="(p, i) in PERIOD_PRESETS"
        :key="p.days"
        :ref="(el) => el && (segments[i] = el as HTMLElement)"
        type="button"
        :aria-pressed="selected === i"
        :aria-disabled="isDisabled(p.days) || undefined"
        :aria-describedby="isDisabled(p.days) ? `${uid}-hint` : undefined"
        :class="[
          'relative min-h-10 whitespace-nowrap rounded-lg px-2 text-label font-semibold sm:min-h-9 sm:px-3',
          selected === i
            ? 'text-sun-on'
            : isDisabled(p.days)
              ? 'cursor-help text-muted underline decoration-dotted decoration-2 underline-offset-4'
              : 'text-muted hover:bg-surface hover:text-fg',
        ]"
        @click="choose(i)"
        @mouseenter="isDisabled(p.days) && showHint()"
        @mouseleave="isDisabled(p.days) && hideHint()"
        @focus="isDisabled(p.days) && showHint()"
        @blur="hideHint"
      >
        {{ t(p.label) }}
      </button>

      <!-- custom: pencil chip + "[45] days" field that slides open inside the control -->
      <div :ref="(el) => el && (segments[CUSTOM] = el as HTMLElement)" class="relative flex min-h-10 items-center rounded-lg sm:min-h-9">
        <button
          type="button"
          :aria-pressed="selected === CUSTOM"
          :aria-expanded="customOpen"
          :aria-controls="`${uid}-days`"
          :class="[
            'flex min-h-10 min-w-10 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg px-2 text-label font-semibold sm:min-h-9 sm:px-3',
            selected === CUSTOM ? 'text-sun-on' : 'text-muted hover:bg-surface hover:text-fg',
          ]"
          @click="openCustom"
        >
          <AppIcon name="pencil" :size="15" />
          <span :class="customOpen ? 'sr-only' : 'sr-only sm:not-sr-only'">{{ t("Custom") }}</span>
        </button>
        <div
          :class="[
            'grid transition-[grid-template-columns,opacity] duration-base',
            customOpen ? 'grid-cols-[1fr] opacity-100' : 'grid-cols-[0fr] opacity-0',
          ]"
        >
          <div class="flex min-w-0 items-center gap-1.5 overflow-hidden">
            <label :for="`${uid}-days`" class="sr-only">{{ t("Number of days to show (up to {max})", { max }) }}</label>
            <input
              :id="`${uid}-days`"
              ref="input"
              v-model="draft"
              type="number"
              inputmode="numeric"
              :min="MIN_PERIOD_DAYS"
              :max="max"
              :tabindex="customOpen ? 0 : -1"
              class="my-1 h-8 w-14 shrink-0 rounded-md border border-sun-on/20 bg-surface px-1.5 text-center text-label font-semibold tabular-nums text-fg [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
              @input="onType"
              @keydown.enter.prevent="apply"
              @blur="apply"
            />
            <span class="whitespace-nowrap pr-3 text-label font-semibold text-sun-on">{{ t("days") }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- why a longer period is not available (yet) -->
    <Transition name="fade">
      <p
        v-show="hint"
        :id="`${uid}-hint`"
        role="tooltip"
        class="absolute right-0 top-full z-20 mt-2 flex w-max max-w-[15rem] items-start gap-2 rounded-lg border border-line bg-surface px-3 py-2 text-label text-fg shadow-pop"
      >
        <AppIcon name="info" :size="16" class="mt-0.5 shrink-0 text-mist-fg" />
        {{ t("Avida forecasts {max} days for now.", { max }) }}
      </p>
    </Transition>
  </div>
</template>
