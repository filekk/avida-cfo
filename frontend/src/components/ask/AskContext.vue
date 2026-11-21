<script setup lang="ts">
import { computed, nextTick, ref, useId } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import CollapseTransition from "@/components/ui/CollapseTransition.vue";
import { t } from "@/i18n";
import type { AskTurn } from "@/stores/ask";
import type { AskSuggestion } from "@/types/api";
import AskTurnItem from "./AskTurnItem.vue";
import SuggestionChips from "./SuggestionChips.vue";

/**
 * "Ask your CFO" inside ONE decision (Action center focus view): a full-width bar between the explanation and the
 * decision buttons – the same place for email-based and forecast-based decisions.
 * Closed: one compact bar ("Questions about this case?") – it does not compete with the verdict or the buttons.
 * Open: chips that fit this case · the answers asked here · a question field.
 * Presentational: the parent picks the chips (components/ask/contextual.ts) and the turns of this case and talks
 * to the ask store. `pick` = chip (send unchanged) · `ask` = typed question (the parent adds the case as subject).
 * Starts open again once there are answers, so coming back to a decision shows what was asked.
 */
const props = defineProps<{ suggestions: AskSuggestion[]; turns: AskTurn[]; asking?: boolean }>();
const emit = defineEmits<{ pick: [question: string]; ask: [question: string]; clear: [] }>();

const MAX = 500;
const open = ref(props.turns.length > 0);
const draft = ref("");
const uid = useId();
const input = ref<HTMLInputElement | null>(null);

function toggle() {
  open.value = !open.value;
  if (open.value) nextTick(() => input.value?.focus({ preventScroll: true }));
}
/** Quick questions on the collapsed bar = the first chips of this case (the same ones the panel shows). */
const quick = computed(() => props.suggestions.slice(0, 3));
const QUICK_VISIBLE = ["hidden md:block", "hidden lg:block", "hidden xl:block"];
/** Chip on the collapsed bar: open the panel and ask at once (the answer appears in the panel). */
function askQuick(question: string) {
  if (props.asking) return;
  open.value = true;
  emit("pick", question);
}
function submit() {
  if (!draft.value.trim() || props.asking) return;
  emit("ask", draft.value);
  draft.value = "";
}
</script>

<template>
  <section class="overflow-hidden rounded-xl border border-line bg-surface" :aria-labelledby="`ctx-ask-${uid}`">
    <!--
      collapsed bar: [icon · title] [2–3 quick questions] [Open · chevron]
      The whole bar toggles (mouse convenience); the title is the real toggle button for keyboard / screen readers.
      Quick questions are their own buttons: click → open the panel AND ask right away (stopPropagation, so the
      bar's own click does not close it again). How many fit: phones 0 (the subtitle explains instead) · md 1 ·
      lg 2 · xl 3 – always one line, long questions are cut with "…" (full text in the tooltip).
    -->
    <div
      :class="[
        'flex min-h-14 cursor-pointer items-center gap-3 px-4 py-2.5 transition-colors duration-fast hover:bg-input/60 sm:px-5',
        open ? 'bg-input/40' : '',
      ]"
      @click="toggle"
    >
      <h3 :id="`ctx-ask-${uid}`" class="min-w-0 shrink-0 md:shrink">
        <button
          type="button"
          class="flex min-h-11 items-center gap-3 rounded-lg text-left"
          :aria-expanded="open"
          :aria-controls="`ctx-ask-panel-${uid}`"
          @click.stop="toggle"
        >
          <AppIcon name="ask" :size="20" class="shrink-0 text-muted" />
          <span class="grid min-w-0 gap-0.5 leading-tight">
            <span class="whitespace-nowrap text-base font-semibold">{{ t("Ask your CFO") }}</span>
            <span :class="['text-label text-muted', quick.length && !open ? 'md:hidden' : '']">
              {{ t("Questions about this case? Pick one below or ask in your own words.") }}
            </span>
          </span>
        </button>
      </h3>

      <Transition name="fade">
        <ul v-if="!open && quick.length" class="flex min-w-0 flex-1 items-center gap-2 overflow-hidden" :aria-label="t('Quick questions')">
          <li v-for="(s, i) in quick" :key="s.id" :class="['min-w-0 max-w-[18rem]', QUICK_VISIBLE[i]]">
            <button
              type="button"
              :disabled="asking"
              :title="s.question"
              class="flex min-h-10 max-w-full items-center gap-1.5 rounded-lg border border-line bg-input px-3 py-1.5 text-label font-medium text-fg transition-colors duration-fast hover:border-fg/40 hover:bg-surface disabled:cursor-not-allowed disabled:opacity-60"
              @click.stop="askQuick(s.question)"
            >
              <AppIcon name="arrowRight" :size="14" class="shrink-0 text-muted" />
              <span class="min-w-0 truncate">{{ s.question }}</span>
            </button>
          </li>
        </ul>
      </Transition>
      <span v-if="open || !quick.length" class="flex-1" aria-hidden="true" />

      <span class="flex shrink-0 items-center gap-2" aria-hidden="true">
        <span class="hidden text-label font-semibold text-gold sm:inline">{{ open ? t("Close") : t("Open") }}</span>
        <span v-if="turns.length" class="rounded-md bg-input px-2 py-0.5 text-caption font-medium tabular-nums text-muted">
          {{ turns.length }}
        </span>
        <AppIcon
          name="chevronDown"
          :size="20"
          :class="['text-muted transition-transform duration-base', open ? 'rotate-180' : '']"
        />
      </span>
    </div>

    <CollapseTransition>
      <div v-if="open" :id="`ctx-ask-panel-${uid}`">
        <div class="grid gap-4 border-t border-line p-4 sm:p-5">
          <SuggestionChips :suggestions="suggestions" :disabled="asking" @pick="(q) => emit('pick', q)" />

          <template v-if="turns.length">
            <ol class="grid max-w-4xl gap-4" aria-live="polite" :aria-label="t('Conversation')">
              <AskTurnItem v-for="turn in turns" :key="turn.id" :turn="turn" />
            </ol>
            <button
              type="button"
              :disabled="asking"
              class="flex min-h-10 w-fit items-center gap-1.5 rounded-lg text-sm font-semibold text-gold underline-offset-4 hover:underline disabled:cursor-not-allowed disabled:opacity-50 disabled:no-underline"
              @click="emit('clear')"
            >
              <AppIcon name="plus" :size="16" />
              {{ t("Start a new conversation") }}
            </button>
          </template>

          <form class="grid max-w-4xl gap-1.5" @submit.prevent="submit">
            <label :for="`ctx-ask-input-${uid}`" class="sr-only">{{ t("Your question about this case") }}</label>
            <div class="flex gap-2">
              <input
                :id="`ctx-ask-input-${uid}`"
                ref="input"
                v-model="draft"
                type="text"
                :maxlength="MAX"
                autocomplete="off"
                enterkeyhint="send"
                :placeholder="t('Ask about this case…')"
                class="min-h-[2.75rem] w-full min-w-0 flex-1 rounded-lg border border-line bg-input px-3 text-fg placeholder:text-muted focus:border-fg/40"
              />
              <BaseButton
                type="submit"
                variant="secondary"
                icon="send"
                :loading="asking"
                :disabled="!draft.trim()"
                :aria-label="t('Ask')"
                class="w-11 shrink-0 !px-0"
              />
            </div>
            <span class="flex items-start gap-1.5 text-caption text-muted">
              <AppIcon name="info" :size="14" class="mt-0.5 shrink-0" />
              {{ t("Typed questions take a few seconds – the AI model writes the answer.") }}
            </span>
          </form>
        </div>
      </div>
    </CollapseTransition>
  </section>
</template>
