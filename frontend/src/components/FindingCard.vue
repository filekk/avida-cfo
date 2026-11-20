<script setup lang="ts">
import { computed, ref } from "vue";
import { eur, fmtDate } from "../api";
import type { Finding } from "../types";
import AutonomyBadge from "./AutonomyBadge.vue";

// Split screen: what the supplier says (left) vs. what the contract says (right).
const props = defineProps<{ f: Finding }>();
const showCalc = ref(false);

const VERDICT = {
  violates: { text: "Not allowed by your contract", cls: "bg-rose-600" },
  allowed: { text: "Allowed by your contract", cls: "bg-emerald-600" },
  unclear: { text: "Cannot be checked – please review", cls: "bg-slate-500" },
};
const v = computed(() => VERDICT[props.f.contract.verdict]);

const title = computed(() => {
  const x = props.f.extraction;
  if (!x.figures_stated) return `${x.party}: change announced – no figures given`;
  if (props.f.kind === "payment_delay") return `${x.party}: pays invoice ${x.invoice} ${x.days_late} days late`;
  return `${x.party}: +${x.increase_pct}% from ${fmtDate(x.effective_date!)}`;
});
</script>

<template>
  <article class="overflow-hidden rounded-2xl bg-white shadow-sm">
    <header :class="['flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-white', v.cls]">
      <span class="text-lg font-bold">
        {{ title }}
      </span>
      <span class="rounded-full bg-white/20 px-3 py-1 text-sm font-semibold">{{ v.text }}</span>
    </header>

    <div class="grid gap-px bg-slate-200 md:grid-cols-2">
      <div class="bg-white p-5">
        <div class="mb-2 flex items-center justify-between text-sm text-slate-500">
          <span>📧 Email from {{ f.email.from_name }}</span>
          <AutonomyBadge level="analyzed" />
        </div>
        <p class="mb-2 font-semibold">{{ f.email.subject }}</p>
        <p class="whitespace-pre-line text-sm text-slate-700">{{ f.email.body }}</p>
      </div>

      <div class="bg-white p-5">
        <div class="mb-2 flex items-center justify-between text-sm text-slate-500">
          <span>📄 {{ f.contract.contract?.title ?? "Contract" }}</span>
          <AutonomyBadge level="recommendation" />
        </div>
        <blockquote v-if="f.contract.quote" class="mb-3 border-l-4 border-amber-400 bg-amber-50 p-3 italic">
          “{{ f.contract.quote }}”
          <footer class="mt-1 text-sm not-italic text-slate-500">
            {{ f.contract.clause_id }}<template v-if="f.contract.clause?.page">, page {{ f.contract.clause.page }}</template>
          </footer>
        </blockquote>
        <p class="mb-3">{{ f.contract.explanation_simple }}</p>
        <ul class="space-y-1 text-sm">
          <li v-for="c in f.contract.checks" :key="c.check">
            {{ c.passed ? "✅" : "❌" }} <b>{{ c.check }}</b>: {{ c.detail }}
          </li>
        </ul>
      </div>
    </div>

    <footer class="flex flex-wrap items-center gap-x-8 gap-y-2 bg-slate-50 px-5 py-3">
      <template v-if="f.kind === 'payment_delay' && f.extraction.figures_stated">
        <span>Arrives: <b>{{ fmtDate(f.extraction.due_date!) }} → {{ fmtDate(f.extraction.new_payment_date!) }}</b></span>
        <span>Lowest balance: <b>{{ eur(-(f.impact.lowest_balance_effect ?? 0)) }}</b></span>
      </template>
      <template v-else-if="f.extraction.figures_stated">
        <span>Extra cost: <b>{{ eur(f.impact.monthly) }}</b>/month</span>
        <span>Next 12 months: <b>{{ eur(f.impact.next_12_months) }}</b></span>
      </template>
      <button class="text-sm text-sky-700 underline" @click="showCalc = !showCalc">
        {{ showCalc ? "Hide calculation" : "Show calculation" }}
      </button>
      <code v-if="showCalc" class="w-full text-sm text-slate-600">{{ f.impact.calculation }}</code>
    </footer>
  </article>
</template>
