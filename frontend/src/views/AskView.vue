<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import AskTurnItem from "@/components/ask/AskTurnItem.vue";
import SuggestionChips from "@/components/ask/SuggestionChips.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { t } from "@/i18n";
import { useAskStore } from "@/stores/ask";

/**
 * "Ask your CFO" – plain-language questions about the company's money, contracts and emails.
 * The backend routes each question to the right agent, which answers only from numbers it already computed.
 * Chips → instant prepared answer · typed → the model (3–7 s) · off-topic → polite refusal + suggestions.
 */
const store = useAskStore();
const { suggestions, note, loadingSuggestions, suggestionsError, turns, asking } = storeToRefs(store);

const MAX = 500;
const draft = ref("");
const list = ref<HTMLElement | null>(null);

function submit() {
  if (!draft.value.trim() || asking.value) return;
  store.ask(draft.value);
  draft.value = "";
}

onMounted(() => {
  if (!suggestions.value.length) store.loadSuggestions();
});

// keep the newest answer in view
watch(
  () => turns.value.map((x) => !!x.answer || !!x.error).join(),
  async () => {
    await nextTick();
    list.value?.lastElementChild?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  },
);
</script>

<template>
  <PageHeader
    :eyebrow="t('Ask your CFO')"
    :title="t('Ask about your money')"
    :description="t('Your agents answer only from your own numbers, contracts and emails – every figure is checked.')"
  />

  <AlertBanner v-if="note" tone="info">{{ note }}</AlertBanner>

  <BaseCard :padded="false">
    <div class="grid gap-5 p-4 sm:p-5">
      <EmptyState
        v-if="!turns.length"
        icon="ask"
        :title="t('What would you like to know?')"
        :description="t('Pick a question below or type your own.')"
      />
      <ol v-else ref="list" class="grid gap-5" aria-live="polite" :aria-label="t('Conversation')">
        <AskTurnItem v-for="turn in turns" :key="turn.id" :turn="turn" />
      </ol>

      <div class="grid gap-2 border-t border-line pt-4">
        <span class="text-label font-semibold text-muted">{{ t("Suggested questions") }}</span>
        <AlertBanner v-if="suggestionsError" tone="warn">
          {{ suggestionsError }}
          <button type="button" class="ml-2 underline" @click="store.loadSuggestions()">{{ t("Try again") }}</button>
        </AlertBanner>
        <div v-else-if="loadingSuggestions && !suggestions.length" class="flex flex-wrap gap-2">
          <SkeletonBlock v-for="i in 3" :key="i" height="h-10" class="w-56" />
        </div>
        <SuggestionChips v-else :suggestions="suggestions" :disabled="asking" @pick="store.ask" />
      </div>

      <form class="grid gap-2" @submit.prevent="submit">
        <label for="ask-input" class="sr-only">{{ t("Your question") }}</label>
        <div class="flex flex-col gap-2 sm:flex-row">
          <input
            id="ask-input"
            v-model="draft"
            type="text"
            :maxlength="MAX"
            autocomplete="off"
            :placeholder="t('e.g. Can I pay my employees in January?')"
            class="min-h-[2.75rem] w-full rounded-lg border border-line bg-input px-3 text-fg placeholder:text-muted focus:border-fg/40"
          />
          <BaseButton type="submit" icon="send" :loading="asking" :disabled="!draft.trim()">{{ t("Ask") }}</BaseButton>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-2 text-caption text-muted">
          <span class="flex items-center gap-1.5">
            <AppIcon name="info" :size="14" /> {{ t("Typed questions take a few seconds – the AI model writes the answer.") }}
          </span>
          <span class="tabular-nums">{{ draft.length }} / {{ MAX }}</span>
        </div>
      </form>

      <button
        v-if="turns.length && !asking"
        type="button"
        class="w-fit text-sm font-semibold text-gold underline-offset-4 hover:underline"
        @click="store.clear()"
      >
        {{ t("Start a new conversation") }}
      </button>
    </div>
  </BaseCard>
</template>
