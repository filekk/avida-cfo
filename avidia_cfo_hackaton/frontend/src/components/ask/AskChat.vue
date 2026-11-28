<script setup lang="ts">
import { nextTick, onMounted, ref, useId, watch } from "vue";
import { storeToRefs } from "pinia";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { t } from "@/i18n";
import { useAskStore } from "@/stores/ask";
import { prefersReducedMotion } from "@/utils/motion";
import AskTurnItem from "./AskTurnItem.vue";
import SuggestionChips from "./SuggestionChips.vue";

/**
 * "Ask your CFO" chat: conversation · suggested questions · question field. Plain-language questions about the
 * company's money, contracts and emails. The backend routes each question to the right agent, which answers only
 * from numbers it already computed. Chip → instant prepared answer · typed → the model (3–7 s) · off-topic → polite
 * refusal + new suggestions.
 *
 * Widget exception (like the top-bar sync/InboxCheck): it reads the app-level ask store directly. It lives in two
 * places that share ONE conversation – the Action center card and the Overview's floating panel (AskLauncher) –
 * and both would only forward every prop and emit 1:1.
 *   default  – sits in a card and grows with the page; the newest turn is scrolled into view in the window
 *   compact  – fills a flex-column parent: the conversation scrolls inside, the question field stays at the bottom
 */
const props = withDefaults(defineProps<{ compact?: boolean }>(), { compact: false });

const store = useAskStore();
// only the overview conversation – questions asked inside an Action center decision live there
const { suggestions, note, loadingSuggestions, suggestionsError, generalTurns: turns, asking } = storeToRefs(store);

const MAX = 500;
const draft = ref("");
const uid = useId();
const inputId = `ask-input-${uid}`;
const hintId = `ask-hint-${uid}`;
const input = ref<HTMLInputElement | null>(null);
const scroller = ref<HTMLElement | null>(null);
const list = ref<HTMLElement | null>(null);

function submit() {
  if (!draft.value.trim() || asking.value) return;
  store.ask(draft.value);
  draft.value = "";
}

onMounted(() => {
  if (!suggestions.value.length && !loadingSuggestions.value) store.loadSuggestions();
});

/**
 * Keep the newest answer in view. Compact: the newest turn moves to the top of the scroll area (question + start
 * of the answer visible, suggestions below if there is room). Default: the window scrolls just enough.
 */
function scrollToLatest(behavior: ScrollBehavior = prefersReducedMotion() ? "auto" : "smooth") {
  const last = list.value?.lastElementChild as HTMLElement | null | undefined;
  if (!last) return;
  const box = scroller.value;
  if (props.compact && box) {
    const top = last.getBoundingClientRect().top - box.getBoundingClientRect().top + box.scrollTop - 16;
    box.scrollTo({ top: Math.max(0, Math.min(top, box.scrollHeight - box.clientHeight)), behavior });
  } else {
    last.scrollIntoView({ block: "nearest", behavior });
  }
}

// a new question → scroll at once; its answer → once the bubble has grown to full height (AskTurnItem @settled)
watch(
  () => turns.value.map((x) => x.id).join(),
  async () => {
    await nextTick();
    scrollToLatest();
  },
);

defineExpose({ focus: () => input.value?.focus(), scrollToLatest });
</script>

<template>
  <div :class="compact ? 'flex min-h-0 flex-1 flex-col' : 'grid gap-5'">
    <!-- conversation + suggestions (compact: this part scrolls, the form below stays put) -->
    <div
      ref="scroller"
      :class="
        compact
          ? 'ask-scroll grid min-h-0 flex-1 content-start gap-4 overflow-y-auto overscroll-contain px-4 py-4'
          : 'grid gap-5'
      "
    >
      <AlertBanner v-if="note" tone="info">{{ note }}</AlertBanner>

      <!-- greeting while the conversation is empty: looks like the agent's first message -->
      <div v-if="!turns.length" class="grid max-w-[92%] gap-1 rounded-lg border border-line bg-surface px-4 py-3">
        <p class="font-semibold">{{ t("What would you like to know?") }}</p>
        <p class="text-label text-muted">{{ t("Pick a question below or type your own.") }}</p>
      </div>

      <template v-else>
        <ol ref="list" class="grid gap-5" aria-live="polite" :aria-label="t('Conversation')">
          <AskTurnItem
            v-for="turn in turns"
            :key="turn.id"
            :turn="turn"
            :class="compact ? '' : 'scroll-mb-6 scroll-mt-28'"
            @settled="scrollToLatest()"
          />
        </ol>
        <!-- disabled (not hidden) while an answer is on its way → nothing below jumps -->
        <button
          type="button"
          :disabled="asking"
          class="flex min-h-11 w-fit items-center gap-1.5 rounded-lg text-sm font-semibold text-gold underline-offset-4 hover:underline disabled:cursor-not-allowed disabled:opacity-50 disabled:no-underline"
          @click="store.clear()"
        >
          <AppIcon name="plus" :size="16" />
          {{ t("Start a new conversation") }}
        </button>
      </template>

      <div class="grid gap-2 border-t border-line pt-4">
        <span class="text-label font-semibold text-muted">{{ t("Suggested questions") }}</span>
        <AlertBanner v-if="suggestionsError" tone="warn">
          {{ suggestionsError }}
          <button type="button" class="ml-2 font-semibold underline" @click="store.loadSuggestions()">{{ t("Try again") }}</button>
        </AlertBanner>
        <div v-else-if="loadingSuggestions && !suggestions.length" class="flex flex-wrap gap-2">
          <SkeletonBlock v-for="i in 3" :key="i" height="h-10" class="w-56 max-w-full" />
        </div>
        <SuggestionChips v-else :suggestions="suggestions" :disabled="asking" @pick="store.ask" />
      </div>
    </div>

    <form
      :class="['grid gap-2', compact ? 'shrink-0 border-t border-line bg-surface px-4 pb-4 pt-3' : '']"
      @submit.prevent="submit"
    >
      <label :for="inputId" class="sr-only">{{ t("Your question") }}</label>
      <div :class="['flex gap-2', compact ? '' : 'flex-col sm:flex-row']">
        <input
          :id="inputId"
          ref="input"
          v-model="draft"
          type="text"
          :maxlength="MAX"
          autocomplete="off"
          enterkeyhint="send"
          :aria-describedby="hintId"
          :placeholder="t('e.g. Can I pay my employees in January?')"
          class="min-h-[2.75rem] w-full min-w-0 flex-1 rounded-lg border border-line bg-input px-3 text-fg placeholder:text-muted focus:border-fg/40"
        />
        <!-- compact: icon-only send button (44px square) with the same accessible name -->
        <BaseButton
          type="submit"
          icon="send"
          :loading="asking"
          :disabled="!draft.trim()"
          :aria-label="compact ? t('Ask') : undefined"
          :class="compact ? 'w-11 shrink-0 !px-0' : ''"
        >
          <template v-if="!compact">{{ t("Ask") }}</template>
        </BaseButton>
      </div>
      <div class="flex flex-wrap items-start justify-between gap-x-3 gap-y-1 text-caption text-muted">
        <span :id="hintId" class="flex min-w-0 flex-1 items-start gap-1.5">
          <AppIcon name="info" :size="14" class="mt-0.5 shrink-0" />
          <span>{{ t("Typed questions take a few seconds – the AI model writes the answer.") }}</span>
        </span>
        <span class="shrink-0 tabular-nums">{{ draft.length }} / {{ MAX }}</span>
      </div>
    </form>
  </div>
</template>

<style scoped>
/* Thin, theme-aware scrollbar inside the compact panel. */
.ask-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgb(var(--c-line)) transparent;
}
</style>
