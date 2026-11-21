<script setup lang="ts">
import { computed, useId } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import SourceTag from "@/components/agent/SourceTag.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { t, tn } from "@/i18n";
import type { UploadResult } from "@/types/api";
import { stagger } from "@/utils/motion";
import ContractWarnings from "./ContractWarnings.vue";
import { ROLE, keyTerms, partyOf, roleOf } from "./contracts";

/**
 * Result of an upload: what Avida read, so the owner can compare it with the paper before trusting it –
 * the key terms it found, the clauses it can quote and what to double-check. Ends with the next step
 * (the contract counts from the next inbox check). Backend texts (title, clause titles, warnings) as delivered.
 *
 * It arrives live from the model, so it fills in in reading order (the card itself rises in ContractsView):
 * read-out line → title → each key term → each clause → warnings → next step. Whole cascade < 1 s.
 */
const props = defineProps<{ result: UploadResult }>();
defineEmits<{ close: [] }>();

const c = computed(() => props.result.contract);
const terms = computed(() => keyTerms(c.value));
const seconds = computed(() => Math.max(1, Math.round(props.result.seconds)));
const headingId = useId();

/** position of every block/row in the cascade (headings count as a step, so each group "opens" first) */
const at = computed(() => {
  const termsAt = 2;
  const clausesAt = termsAt + (terms.value.length ? terms.value.length + 1 : 0);
  const warningsAt = clausesAt + (c.value.clauses.length ? c.value.clauses.length + 1 : 0);
  const noteAt = warningsAt + (c.value.warnings.length ? 1 : 0);
  return { termsAt, clausesAt, warningsAt, noteAt, total: noteAt + 1 };
});
const rise = (i: number) => stagger(i, at.value.total);
</script>

<template>
  <section class="grid gap-4 rounded-xl border border-line bg-surface p-4" :aria-labelledby="headingId">
    <header class="flex items-start gap-3">
      <AppIcon name="checkCircle" :size="20" class="mt-0.5 shrink-0 text-positive" />
      <div class="grid min-w-0 flex-1 gap-0.5">
        <h3 :id="headingId" class="flex flex-wrap items-baseline gap-x-2 text-base font-semibold leading-snug">
          {{ t("Contract added") }}
          <SourceTag :source="result.source" />
        </h3>
        <p class="break-words text-label text-muted">{{ partyOf(c) }} · {{ t(ROLE[roleOf(c)].label) }}</p>
      </div>
      <button
        type="button"
        class="-mr-2 -mt-2 grid h-11 w-11 shrink-0 place-items-center rounded-lg text-muted hover:bg-input hover:text-fg"
        :aria-label="t('Close')"
        :title="t('Close')"
        @click="$emit('close')"
      >
        <AppIcon name="x" :size="18" />
      </button>
    </header>

    <div class="flex flex-wrap items-center gap-x-3 gap-y-2 animate-rise" :style="rise(0)">
      <AutonomyBadge level="analyzed" />
      <span class="text-label text-muted">
        {{ tn(result.pages, "{n} page", "{n} pages") }} · {{ tn(seconds, "read in {n} second", "read in {n} seconds") }}
      </span>
    </div>

    <p class="break-words text-label leading-snug animate-rise" :style="rise(1)">{{ c.title }}</p>

    <!-- the box appears with its heading, then its rows fill in one by one -->
    <div v-if="terms.length" class="grid gap-2">
      <h4 class="eyebrow animate-rise" :style="rise(at.termsAt)">{{ t("What Avida found") }}</h4>
      <dl class="grid divide-y divide-line rounded-lg border border-line animate-rise" :style="rise(at.termsAt)">
        <div
          v-for="(term, i) in terms"
          :key="term.label"
          class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5 px-3 py-2.5 animate-rise"
          :style="rise(at.termsAt + 1 + i)"
        >
          <dt class="text-label text-muted">{{ term.label }}</dt>
          <dd class="font-semibold tabular-nums">{{ term.value }}</dd>
        </div>
      </dl>
    </div>

    <div v-if="c.clauses.length" class="grid gap-2">
      <h4 class="eyebrow animate-rise" :style="rise(at.clausesAt)">{{ t("Clauses Avida can quote") }}</h4>
      <ul class="grid gap-1.5 text-label">
        <li
          v-for="(cl, i) in c.clauses"
          :key="cl.id"
          class="grid grid-cols-[auto_minmax(0,1fr)] items-baseline gap-2 animate-rise"
          :style="rise(at.clausesAt + 1 + i)"
        >
          <span class="rounded bg-input px-1.5 py-0.5 font-mono text-caption">{{ cl.id }}</span>
          <span class="break-words">{{ cl.title }}</span>
        </li>
      </ul>
    </div>

    <ContractWarnings v-if="c.warnings.length" :warnings="c.warnings" class="animate-rise" :style="rise(at.warningsAt)" />

    <p class="flex items-start gap-2 border-t border-line pt-3 text-label text-muted animate-rise" :style="rise(at.noteAt)">
      <AppIcon name="info" :size="16" class="mt-0.5" />
      <span>{{ t("Avida uses this contract from your next inbox check. Start it with “{button}” at the top.", { button: t("Check my inbox") }) }}</span>
    </p>
  </section>
</template>
