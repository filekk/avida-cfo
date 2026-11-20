<script setup lang="ts">
import { computed, ref } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import StatTile from "@/components/ui/StatTile.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { VERDICT } from "@/constants/autonomy";
import type { Finding } from "@/types/api";
import { eur, fmtDate, pct } from "@/utils/format";
import PriceBar from "./PriceBar.vue";
import { verdictTone } from "./verdict";

/**
 * The core of "explainable", drawn as a 3-step flow: what the email says → what the contract says → verdict,
 * with the money underneath. The full email and the formula stay one click away instead of filling the screen.
 */
const props = defineProps<{ finding: Finding }>();
const showEmail = ref(false);
const showCalc = ref(false);
const v = computed(() => VERDICT[props.finding.contract.verdict]);
const tone = computed(() => verdictTone(props.finding.contract.verdict));
const c = computed(() => props.finding.contract);
const ex = computed(() => props.finding.extraction);
</script>

<template>
  <article class="overflow-hidden rounded-xl border border-line bg-surface shadow-card">
    <header class="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
      <div class="flex min-w-0 items-center gap-3">
        <span class="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-input font-display text-lg font-extrabold" aria-hidden="true">
          {{ ex.supplier.charAt(0) }}
        </span>
        <div class="grid min-w-0">
          <h2 class="text-lg font-bold">{{ ex.supplier }}: {{ pct(ex.increase_pct) }}</h2>
          <span class="text-sm text-muted">from {{ fmtDate(ex.effective_date) }}</span>
        </div>
      </div>
      <StatusPill :tone="v.tone"><AppIcon :name="v.icon" :size="13" />{{ v.label }}</StatusPill>
    </header>

    <div class="grid gap-3 p-4 sm:p-5 lg:grid-cols-[1fr_auto_1fr_auto_1fr]">
      <!-- 1 · the email -->
      <section class="grid content-start gap-3 rounded-xl bg-input/60 p-4" aria-label="What the email says">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="flex items-center gap-2 text-sm font-bold">
            <span class="grid h-8 w-8 place-items-center rounded-lg bg-surface text-muted"><AppIcon name="mail" /></span>
            The email says
          </span>
          <AutonomyBadge level="analyzed" />
        </div>
        <p :class="['font-display text-3xl font-extrabold tabular-nums', tone.text]">{{ pct(ex.increase_pct) }}</p>
        <PriceBar :from="ex.old_monthly" :to="ex.new_monthly" :tone="tone.bar" />
        <button
          type="button"
          class="flex w-fit items-center gap-1.5 text-sm font-semibold text-gold hover:underline"
          :aria-expanded="showEmail"
          @click="showEmail = !showEmail"
        >
          {{ showEmail ? "Hide the email" : `Read the email from ${finding.email.from_name}` }}
          <AppIcon name="chevronDown" :class="['transition-transform', showEmail ? 'rotate-180' : '']" />
        </button>
        <div v-if="showEmail" class="grid gap-2 rounded-lg bg-surface p-3 text-sm">
          <p class="font-semibold">{{ finding.email.subject }}</p>
          <p class="whitespace-pre-line leading-relaxed text-muted">{{ finding.email.body }}</p>
        </div>
      </section>

      <span class="grid place-items-center" aria-hidden="true">
        <span class="grid h-8 w-8 place-items-center rounded-full border border-line bg-surface text-muted">
          <AppIcon name="arrowDown" class="lg:hidden" /><AppIcon name="arrowRight" class="hidden lg:block" />
        </span>
      </span>

      <!-- 2 · the contract -->
      <section class="grid content-start gap-3 rounded-xl bg-input/60 p-4" aria-label="What your contract says">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="flex items-center gap-2 text-sm font-bold">
            <span class="grid h-8 w-8 place-items-center rounded-lg bg-surface text-muted"><AppIcon name="document" /></span>
            Your contract says
          </span>
          <AutonomyBadge level="analyzed" />
        </div>
        <p class="text-sm font-semibold">{{ c.contract?.title ?? "No contract on file" }}</p>
        <blockquote v-if="c.quote" class="rounded-r-lg border-l-4 border-sun bg-surface p-3">
          <p class="text-[0.92rem] italic leading-relaxed">“{{ c.quote }}”</p>
          <footer class="mt-2 flex flex-wrap gap-x-2 text-[0.8rem] font-semibold text-muted">
            <span>{{ c.clause_id }}</span>
            <span v-if="c.clause?.title">· {{ c.clause.title }}</span>
            <span v-if="c.clause?.page">· page {{ c.clause.page }}</span>
          </footer>
        </blockquote>
      </section>

      <span class="grid place-items-center" aria-hidden="true">
        <span class="grid h-8 w-8 place-items-center rounded-full border border-line bg-surface text-muted">
          <AppIcon name="arrowDown" class="lg:hidden" /><AppIcon name="arrowRight" class="hidden lg:block" />
        </span>
      </span>

      <!-- 3 · the verdict -->
      <section :class="['grid content-start gap-3 rounded-xl p-4', tone.panel]" aria-label="Verdict">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="flex items-center gap-2 text-sm font-bold">
            <span class="grid h-8 w-8 place-items-center rounded-lg bg-surface text-muted"><AppIcon name="scale" /></span>
            Verdict
          </span>
          <AutonomyBadge level="recommendation" />
        </div>
        <p class="flex items-center gap-2.5 font-display text-lg font-bold leading-tight">
          <AppIcon :name="v.icon" :size="28" :class="tone.text" />
          {{ v.label }}
        </p>
        <p class="text-sm leading-relaxed">{{ c.explanation_simple }}</p>
        <ul v-if="c.checks.length" class="grid gap-2 border-t border-fg/10 pt-3">
          <li v-for="chk in c.checks" :key="chk.check" class="grid grid-cols-[auto_1fr] gap-2 text-sm">
            <AppIcon
              :name="chk.passed ? 'checkCircle' : 'xCircle'"
              :size="17"
              :class="['mt-0.5', chk.passed ? 'text-positive' : 'text-negative']"
            />
            <span class="grid leading-snug">
              <b>{{ chk.check }}<span class="sr-only">{{ chk.passed ? " (passed)" : " (failed)" }}</span></b>
              <span class="text-[0.8rem] text-muted">{{ chk.detail }} · {{ chk.clause_id }}</span>
            </span>
          </li>
        </ul>
      </section>
    </div>

    <!-- the money -->
    <footer class="grid gap-4 border-t border-line bg-input/40 px-5 py-4">
      <div class="grid gap-4 sm:grid-cols-3">
        <StatTile icon="euro" label="Extra per month" :value="eur(finding.impact.monthly)" />
        <StatTile icon="chart" label="Within your forecast" :value="eur(finding.impact.in_horizon)" />
        <StatTile icon="calendar" label="Next 12 months" :value="eur(finding.impact.next_12_months)" :tone="tone.stat" />
      </div>
      <button
        type="button"
        class="flex w-fit items-center gap-1.5 text-sm font-semibold text-gold hover:underline"
        :aria-expanded="showCalc"
        @click="showCalc = !showCalc"
      >
        <AppIcon name="calculator" /> {{ showCalc ? "Hide calculation" : "Show calculation" }}
      </button>
      <code v-if="showCalc" class="block rounded-lg bg-surface p-3 font-mono text-[0.82rem] text-muted">{{ finding.impact.calculation }}</code>
    </footer>

    <!-- optional: the related decision, part of the same card (finding detail only) -->
    <div v-if="$slots.default" class="border-t border-line">
      <slot />
    </div>
  </article>
</template>
