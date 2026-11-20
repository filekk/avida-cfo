<script setup lang="ts">
import { computed, ref } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { VERDICT } from "@/constants/autonomy";
import type { Finding } from "@/types/api";
import { eur, fmtDate, pct } from "@/utils/format";

/**
 * Split screen – the core of "explainable": what the supplier says (left) ↔ what the contract says (right)
 * ↔ the calculation (footer, behind "Show calculation").
 */
const props = defineProps<{ finding: Finding }>();
const showCalc = ref(false);
const v = computed(() => VERDICT[props.finding.contract.verdict]);
const c = computed(() => props.finding.contract);
</script>

<template>
  <article class="overflow-hidden rounded-xl border border-line bg-surface">
    <header class="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
      <h2 class="text-lg font-bold">
        {{ finding.extraction.supplier }}: {{ pct(finding.extraction.increase_pct) }} from {{ fmtDate(finding.extraction.effective_date) }}
      </h2>
      <StatusPill :tone="v.tone">{{ v.label }}</StatusPill>
    </header>

    <div class="grid md:grid-cols-2 md:divide-x md:divide-line">
      <!-- LEFT: the email -->
      <section class="grid content-start gap-3 p-5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="flex items-center gap-2 text-sm font-semibold text-muted">
            <AppIcon name="mail" /> Email from {{ finding.email.from_name }}
          </span>
          <AutonomyBadge level="analyzed" />
        </div>
        <p class="font-semibold">{{ finding.email.subject }}</p>
        <p class="whitespace-pre-line rounded-lg bg-input p-4 text-sm leading-relaxed">{{ finding.email.body }}</p>
        <p class="text-sm text-muted">
          Avida read: <b class="text-fg">{{ eur(finding.extraction.old_monthly) }} → {{ eur(finding.extraction.new_monthly) }}</b> per month.
        </p>
      </section>

      <!-- RIGHT: the contract -->
      <section class="grid content-start gap-3 border-t border-line p-5 md:border-t-0">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="flex items-center gap-2 text-sm font-semibold text-muted">
            <AppIcon name="document" /> {{ c.contract?.title ?? "No contract on file" }}
          </span>
          <AutonomyBadge level="recommendation" />
        </div>

        <blockquote v-if="c.quote" class="rounded-r-lg border-l-4 border-sun bg-warn-soft/60 p-4">
          <p class="italic">“{{ c.quote }}”</p>
          <footer class="mt-2 text-sm text-muted">
            {{ c.clause_id }}<template v-if="c.clause?.title"> · {{ c.clause.title }}</template>
            <template v-if="c.clause?.page"> · page {{ c.clause.page }}</template>
          </footer>
        </blockquote>

        <p>{{ c.explanation_simple }}</p>

        <ul v-if="c.checks.length" class="grid gap-2">
          <li v-for="chk in c.checks" :key="chk.check" class="flex gap-2 text-sm">
            <AppIcon
              :name="chk.passed ? 'checkCircle' : 'xCircle'"
              :size="17"
              :class="['mt-0.5', chk.passed ? 'text-positive' : 'text-negative']"
            />
            <span>
              <b>{{ chk.check }}</b>
              <span class="sr-only">{{ chk.passed ? "(passed)" : "(failed)" }}</span>:
              {{ chk.detail }} <span class="text-muted">({{ chk.clause_id }})</span>
            </span>
          </li>
        </ul>
      </section>
    </div>

    <!-- FOOTER: the money -->
    <footer class="grid gap-2 border-t border-line bg-input/60 px-5 py-4">
      <div class="flex flex-wrap items-center gap-x-8 gap-y-2">
        <span>Extra cost: <b class="tabular-nums">{{ eur(finding.impact.monthly) }}</b>/month</span>
        <span>In the forecast window: <b class="tabular-nums">{{ eur(finding.impact.in_horizon) }}</b></span>
        <span>Next 12 months: <b class="tabular-nums text-negative">{{ eur(finding.impact.next_12_months) }}</b></span>
        <button type="button" class="text-sm font-semibold text-gold underline underline-offset-2" @click="showCalc = !showCalc">
          {{ showCalc ? "Hide calculation" : "Show calculation" }}
        </button>
      </div>
      <code v-if="showCalc" class="block rounded-lg bg-surface p-3 font-mono text-[0.82rem] text-muted">{{ finding.impact.calculation }}</code>
    </footer>
  </article>
</template>
