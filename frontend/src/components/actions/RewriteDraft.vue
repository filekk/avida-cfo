<script setup lang="ts">
import { nextTick, ref, useId, watch, watchEffect } from "vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import { usePopover } from "@/composables/usePopover";
import { t } from "@/i18n";

/**
 * "AV Rewrite": the owner tells the AI in a few words how the draft should change ("be firmer", "mention the
 * discount") and gets a new draft in the editor. It only rewrites the text – nothing is sent; the owner still
 * decides with "Approve and send". Presentational: emits the wish, the parent (store) talks to the API.
 * Same open/close behaviour as the top-bar pop-ups (usePopover): click to open, Escape / click outside closes.
 * Narrow screens: the trigger is full width and the panel opens under it at the same width.
 */
const props = defineProps<{ busy?: boolean; error?: string | null; disabled?: boolean }>();
const emit = defineEmits<{ submit: [instruction: string] }>();

const MAX = 200;
/** Quick wishes – English source, translated where shown and sent in the UI language. */
const QUICK = ["Be firmer", "Be friendlier", "Make it shorter", "Mention a 2 % discount for paying early"];

const { open, root, trigger, close, onTriggerClick, onFocusOut } = usePopover({
  onKeyboardOpen: () => nextTick(() => field.value?.focus()),
});
const field = ref<HTMLInputElement | null>(null);
// usePopover wants the trigger ELEMENT (focus returns to it on Escape) – BaseButton's root element
const btn = ref<InstanceType<typeof BaseButton> | null>(null);
watchEffect(() => (trigger.value = (btn.value?.$el as HTMLElement | undefined) ?? null));
const wish = ref("");
const uid = useId();

function submit(text = wish.value) {
  const w = text.trim();
  if (!w || props.busy) return;
  emit("submit", w);
}

// success (busy ended without an error) → close and clear; an error keeps the panel open so it is seen
watch(
  () => props.busy,
  (busy, was) => {
    if (was && !busy && !props.error) {
      wish.value = "";
      close();
    }
  },
);
watch(open, (o) => o && nextTick(() => field.value?.focus()));
</script>

<template>
  <div ref="root" class="relative w-full sm:w-auto" @focusout="onFocusOut">
    <BaseButton
      ref="btn"
      size="lg"
      variant="secondary"
      icon="sparkles"
      class="w-full sm:w-auto"
      :loading="busy"
      :disabled="disabled"
      :aria-expanded="open"
      :aria-controls="`rewrite-${uid}`"
      aria-haspopup="dialog"
      @click="onTriggerClick"
    >
      {{ busy ? t("Rewriting…") : t("AV Rewrite") }}
    </BaseButton>

    <Transition
      enter-active-class="transition duration-base ease-out"
      leave-active-class="transition duration-fast ease-out"
      enter-from-class="opacity-0 scale-95 -translate-y-1"
      leave-to-class="opacity-0 scale-95 -translate-y-1"
    >
      <div
        v-if="open"
        :id="`rewrite-${uid}`"
        role="dialog"
        :aria-label="t('Rewrite the draft with AI')"
        class="absolute right-0 top-full z-20 mt-2 grid w-full origin-top-right gap-3 rounded-xl border border-line bg-surface p-4 text-fg shadow-pop sm:w-[24rem] sm:max-w-[calc(100vw-2rem)]"
      >
        <div class="grid gap-0.5">
          <p class="flex items-center gap-2 font-semibold">
            <AppIcon name="sparkles" :size="18" class="text-gold" />
            {{ t("How should the email change?") }}
          </p>
          <p class="text-label text-muted">{{ t("Avida rewrites the draft. Nothing is sent – you read it first.") }}</p>
        </div>

        <ul class="flex flex-wrap gap-2" :aria-label="t('Quick wishes')">
          <li v-for="q in QUICK" :key="q">
            <button
              type="button"
              :disabled="busy"
              class="min-h-9 rounded-lg border border-line bg-surface px-3 py-1 text-left text-label font-medium hover:border-fg/40 hover:bg-input/60 disabled:opacity-60"
              @click="submit(t(q))"
            >
              {{ t(q) }}
            </button>
          </li>
        </ul>

        <form class="grid gap-2" @submit.prevent="submit()">
          <label :for="`rewrite-input-${uid}`" class="sr-only">{{ t("Your wish for the email") }}</label>
          <div class="flex gap-2">
            <input
              :id="`rewrite-input-${uid}`"
              ref="field"
              v-model="wish"
              type="text"
              :maxlength="MAX"
              autocomplete="off"
              enterkeyhint="send"
              :placeholder="t('e.g. be firmer, mention the discount')"
              class="min-h-[2.75rem] w-full min-w-0 flex-1 rounded-lg border border-line bg-input px-3 text-fg placeholder:text-muted focus:border-fg/40"
            />
            <BaseButton type="submit" icon="sparkles" :loading="busy" :disabled="!wish.trim()" class="shrink-0">
              {{ t("Rewrite") }}
            </BaseButton>
          </div>
          <span class="text-right text-caption tabular-nums text-muted">{{ wish.length }} / {{ MAX }}</span>
        </form>

        <AlertBanner v-if="error" tone="warn" role="alert">{{ error }}</AlertBanner>
      </div>
    </Transition>
  </div>
</template>
