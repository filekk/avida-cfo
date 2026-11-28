<script setup lang="ts">
import { computed, nextTick, ref, useId } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { usePopover } from "@/composables/usePopover";
import { LOCALES, locale, setLocale, t, type Locale } from "@/i18n";

/**
 * Language switch, top-right next to the accessibility menu: EN / DE. Same pop-up behaviour as the
 * accessibility menu (hover opens for mouse users, click/tap/keyboard pins it). The whole UI switches instantly.
 */
const panel = ref<HTMLElement | null>(null);
const { open, root, trigger, close, onPointerEnter, onPointerLeave, onTriggerClick, onFocusOut } = usePopover({
  hover: true,
  onKeyboardOpen: () => nextTick(() => panel.value?.querySelector<HTMLElement>("input:checked")?.focus()),
});
const panelId = `lang-${useId()}`;
const current = computed(() => LOCALES.find((l) => l.code === locale.value) ?? LOCALES[0]);

function choose(code: Locale) {
  setLocale(code);
  close(true);
}
</script>

<template>
  <div ref="root" class="relative" @pointerenter="onPointerEnter" @pointerleave="onPointerLeave" @focusout="onFocusOut">
    <button
      ref="trigger"
      type="button"
      :class="[
        'flex h-10 min-w-10 items-center justify-center gap-1.5 rounded-lg border px-2 text-label font-semibold text-fg sm:px-2.5',
        open ? 'border-fg/40 bg-mist' : 'border-line bg-surface hover:bg-mist',
      ]"
      :aria-label="t('Language: {lang}', { lang: current.label })"
      :title="t('Language')"
      :aria-expanded="open"
      :aria-controls="panelId"
      @click="onTriggerClick"
    >
      <AppIcon name="languages" :size="18" class="hidden sm:block" />
      <!-- both codes stacked in one cell → switching never changes the button width -->
      <span class="grid [&>*]:col-start-1 [&>*]:row-start-1" aria-hidden="true">
        <span
          v-for="l in LOCALES"
          :key="l.code"
          :class="['transition-[opacity,transform] duration-base', l.code === locale ? 'opacity-100' : 'translate-y-1 opacity-0']"
        >{{ l.short }}</span>
      </span>
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
        :aria-label="t('Language')"
        class="absolute right-0 top-full z-30 mt-2 grid w-56 max-w-[calc(100vw-2rem)] origin-top-right gap-1 rounded-xl border border-line bg-surface p-2 text-fg shadow-pop"
      >
        <p class="px-2 pb-1 pt-1 text-caption font-medium text-muted">{{ t("Language") }}</p>
        <div role="radiogroup" :aria-label="t('Language')" class="grid gap-1">
          <label
            v-for="l in LOCALES"
            :key="l.code"
            :class="[
              'flex min-h-11 cursor-pointer items-center gap-3 rounded-lg px-2.5 text-label font-semibold',
              'has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px] has-[:focus-visible]:outline-offset-1 has-[:focus-visible]:outline-sun',
              l.code === locale ? 'bg-sun text-sun-on' : 'hover:bg-input',
            ]"
          >
            <input
              type="radio"
              class="sr-only"
              :name="panelId"
              :value="l.code"
              :checked="l.code === locale"
              @change="choose(l.code)"
              @keydown.enter.prevent="choose(l.code)"
            />
            <span
              :class="[
                'grid h-7 w-9 place-items-center rounded-md text-caption font-semibold',
                l.code === locale ? 'bg-sun-on/10' : 'bg-input text-muted',
              ]"
              aria-hidden="true"
            >{{ l.short }}</span>
            <span class="flex-1" :lang="l.code">{{ l.label }}</span>
            <AppIcon
              name="check"
              :size="16"
              :class="['transition-opacity duration-base', l.code === locale ? 'opacity-100' : 'opacity-0']"
            />
          </label>
        </div>
      </section>
    </Transition>
  </div>
</template>
