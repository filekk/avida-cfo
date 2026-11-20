<script setup lang="ts">
import { computed, ref } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import CollapseTransition from "@/components/ui/CollapseTransition.vue";
import IconTile from "@/components/ui/IconTile.vue";
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
/**
 * `bare`:    no frame and no header – the parent (Action center focus view) already shows both.
 * `stacked`: always vertical (email ↓ contract ↓ verdict), for narrow containers.
 */
const props = defineProps<{ finding: Finding; bare?: boolean; stacked?: boolean }>();
const showEmail = ref(false);
const showCalc = ref(false);
const v = computed(() => VERDICT[props.finding.contract.verdict]);
const tone = computed(() => verdictTone(props.finding.contract.verdict));
const c = computed(() => props.finding.contract);
const ex = computed(() => props.finding.extraction);

const TOGGLE =
  "group flex w-fit items-center gap-1.5 rounded-lg py-1 text-sm font-semibold text-gold underline-offset-4 hover:underline";
</script>

<template>
  <article :class="bare ? '' : 'overflow-hidden rounded-xl border border-line bg-surface shadow-card'">
    <header v-if="!bare" class="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
      <div class="flex min-w-0 items-center gap-3">
        <IconTile tone="neutral" class="!text-fg">{{ ex.supplier.charAt(0) }}</IconTile>
        <div class="grid min-w-0 gap-0.5">
          <h2 class="text-xl font-bold leading-tight">
            {{ ex.supplier }}: <span :class="tone.text">{{ pct(ex.increase_pct) }}</span>
          </h2>
          <span class="text-label text-muted">from {{ fmtDate(ex.effective_date) }}</span>
        </div>
      </div>
      <StatusPill :tone="v.tone"><AppIcon :name="v.icon" :size="14" />{{ v.label }}</StatusPill>
    </header>

    <div :class="['grid gap-3', bare ? '' : 'p-4 sm:p-5', stacked ? '' : 'lg:grid-cols-[1fr_auto_1fr_auto_1fr]']">
      <!-- 1 · the email -->
      <section class="grid content-start gap-3 rounded-xl bg-input p-4" aria-label="What the email says">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="flex items-center gap-2.5 text-base font-bold">
            <IconTile icon="mail" tone="neutral" size="sm" class="!bg-surface" />
            The email says
          </span>
          <AutonomyBadge level="analyzed" />
        </div>
        <p :class="['font-display text-3xl font-extrabold tabular-nums', tone.text]">{{ pct(ex.increase_pct) }}</p>
        <PriceBar :from="ex.old_monthly" :to="ex.new_monthly" :tone="tone.bar" />
        <button type="button" :class="TOGGLE" :aria-expanded="showEmail" @click="showEmail = !showEmail">
          {{ showEmail ? "Hide the email" : `Read the email from ${finding.email.from_name}` }}
          <AppIcon name="chevronDown" :size="18" :class="['transition-transform duration-base', showEmail ? 'rotate-180' : '']" />
        </button>
        <CollapseTransition>
          <div v-if="showEmail">
            <div class="grid gap-2 rounded-lg bg-surface p-3 text-sm">
              <p class="font-semibold">{{ finding.email.subject }}</p>
              <p class="whitespace-pre-line leading-relaxed text-muted">{{ finding.email.body }}</p>
            </div>
          </div>
        </CollapseTransition>
      </section>

      <span class="grid place-items-center" aria-hidden="true">
        <span class="grid h-9 w-9 place-items-center rounded-full border border-line bg-surface text-muted">
          <AppIcon name="arrowDown" :size="18" :class="stacked ? '' : 'lg:hidden'" /><AppIcon v-if="!stacked" name="arrowRight" :size="18" class="hidden lg:block" />
        </span>
      </span>

      <!-- 2 · the contract -->
      <section class="grid content-start gap-3 rounded-xl bg-input p-4" aria-label="What your contract says">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="flex items-center gap-2.5 text-base font-bold">
            <IconTile icon="document" tone="neutral" size="sm" class="!bg-surface" />
            Your contract says
          </span>
          <AutonomyBadge level="analyzed" />
        </div>
        <p class="text-sm font-semibold">{{ c.contract?.title ?? "No contract on file" }}</p>
        <blockquote v-if="c.quote" class="rounded-r-lg border-l-4 border-sun bg-surface p-3">
          <p class="italic leading-relaxed">“{{ c.quote }}”</p>
          <footer class="mt-2 flex flex-wrap gap-x-2 text-label font-semibold text-muted">
            <span>{{ c.clause_id }}</span>
            <span v-if="c.clause?.title">· {{ c.clause.title }}</span>
            <span v-if="c.clause?.page">· page {{ c.clause.page }}</span>
          </footer>
        </blockquote>
      </section>

      <span class="grid place-items-center" aria-hidden="true">
        <span class="grid h-9 w-9 place-items-center rounded-full border border-line bg-surface text-muted">
          <AppIcon name="arrowDown" :size="18" :class="stacked ? '' : 'lg:hidden'" /><AppIcon v-if="!stacked" name="arrowRight" :size="18" class="hidden lg:block" />
        </span>
      </span>

      <!-- 3 · the verdict -->
      <section :class="['grid content-start gap-3 rounded-xl p-4', tone.panel]" aria-label="Verdict">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="flex items-center gap-2.5 text-base font-bold">
            <IconTile icon="scale" tone="neutral" size="sm" class="!bg-surface" />
            Verdict
          </span>
          <AutonomyBadge level="recommendation" />
        </div>
        <p class="flex items-center gap-2.5 font-display text-xl font-bold leading-tight">
          <AppIcon :name="v.icon" :size="30" :class="tone.text === 'text-fg' ? 'text-positive' : tone.text" />
          {{ v.label }}
        </p>
        <p class="leading-relaxed">{{ c.explanation_simple }}</p>
        <ul v-if="c.checks.length" class="grid gap-2.5 border-t border-fg/10 pt-3">
          <li v-for="chk in c.checks" :key="chk.check" class="grid grid-cols-[auto_1fr] gap-2 text-sm">
            <AppIcon
              :name="chk.passed ? 'checkCircle' : 'xCircle'"
              :size="18"
              :class="['mt-0.5', chk.passed ? 'text-positive' : 'text-negative']"
            />
            <span class="grid gap-0.5 leading-snug">
              <b>{{ chk.check }}<span class="sr-only">{{ chk.passed ? " (passed)" : " (failed)" }}</span></b>
              <span class="text-label text-muted">{{ chk.detail }} · {{ chk.clause_id }}</span>
            </span>
          </li>
        </ul>
      </section>
    </div>

    <!-- the money: red = what the increase costs you (if not allowed), navy = a legitimate cost -->
    <footer :class="['grid gap-4', bare ? 'mt-4 rounded-xl bg-input/50 p-4' : 'border-t border-line bg-input/50 px-5 py-4']">
      <div :class="['grid gap-4', stacked ? 'sm:grid-cols-2' : 'sm:grid-cols-3']">
        <StatTile icon="euro" label="Extra per month" :value="eur(finding.impact.monthly)" :tone="tone.stat" />
        <StatTile icon="chart" label="Within your forecast" :value="eur(finding.impact.in_horizon)" :tone="tone.stat" />
        <StatTile icon="calendar" label="Next 12 months" :value="eur(finding.impact.next_12_months)" :tone="tone.stat" />
      </div>
      <button type="button" :class="TOGGLE" :aria-expanded="showCalc" @click="showCalc = !showCalc">
        <AppIcon name="calculator" :size="18" /> {{ showCalc ? "Hide calculation" : "Show calculation" }}
        <AppIcon name="chevronDown" :size="18" :class="['transition-transform duration-base', showCalc ? 'rotate-180' : '']" />
      </button>
      <CollapseTransition>
        <div v-if="showCalc">
          <code class="block whitespace-pre-wrap rounded-lg bg-surface p-3 font-mono text-label text-muted">{{ finding.impact.calculation }}</code>
        </div>
      </CollapseTransition>
    </footer>
  </article>
</template>
