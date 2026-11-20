<script setup lang="ts">
import { computed, ref } from "vue";
import { eur, fmtDate } from "../api";
import type { Action } from "../types";
import AutonomyBadge from "./AutonomyBadge.vue";

// Nothing leaves the system without the owner pressing "Approve".
const props = defineProps<{ a: Action }>();
const emit = defineEmits<{ decide: [id: string, approve: boolean, body?: string] }>();

const body = ref<string>(props.a.payload.body ?? "");
const pending = computed(() => props.a.status === "pending");

const approve = () => emit("decide", props.a.id, true, props.a.type === "send_email" ? body.value : undefined);
const decline = () => emit("decide", props.a.id, false);
</script>

<template>
  <article class="rounded-2xl border-2 border-rose-200 bg-white p-5 shadow-sm">
    <div class="mb-2 flex flex-wrap gap-2">
      <AutonomyBadge level="approval" />
      <AutonomyBadge level="simulated" />
    </div>
    <h3 class="text-xl font-bold">{{ a.title }}</h3>
    <p class="mt-1 text-slate-700"><b>Why: </b>{{ a.why }}</p>

    <label v-if="a.type === 'send_email'" class="mt-3 block">
      <span class="text-sm text-slate-500">Draft email to {{ a.payload.to }} – you can edit it before sending</span>
      <textarea
        v-model="body"
        :disabled="!pending"
        class="mt-1 h-56 w-full rounded-lg border border-slate-300 p-3 font-mono text-sm disabled:bg-slate-50"
      />
    </label>

    <dl v-if="a.type === 'credit_application'" class="mt-3 grid grid-cols-2 gap-2 rounded-lg bg-slate-50 p-3 text-sm sm:grid-cols-4">
      <div><dt class="text-slate-500">Product</dt><dd class="font-semibold">{{ a.payload.product }}</dd></div>
      <div><dt class="text-slate-500">Amount</dt><dd class="font-semibold">{{ eur(a.payload.amount) }}</dd></div>
      <div>
        <dt class="text-slate-500">Needed</dt>
        <dd class="font-semibold">{{ fmtDate(a.payload.from) }} – {{ fmtDate(a.payload.until) }}</dd>
      </div>
      <div><dt class="text-slate-500">Max. interest</dt><dd class="font-semibold">{{ eur(a.payload.max_interest_cost) }}</dd></div>
      <p class="col-span-full text-slate-500">{{ a.payload.calculation }} {{ a.payload.note }}</p>
    </dl>

    <div v-if="pending" class="mt-4 flex flex-wrap gap-3">
      <button class="rounded-xl bg-emerald-600 px-6 py-3 text-lg font-bold text-white hover:bg-emerald-700" @click="approve">
        ✓ Approve {{ a.type === "send_email" ? "and send" : "and apply" }}
      </button>
      <button class="rounded-xl bg-slate-200 px-6 py-3 text-lg font-semibold hover:bg-slate-300" @click="decline">
        Not now
      </button>
    </div>
    <p
      v-else
      :class="['mt-4 rounded-lg p-3 font-semibold', a.status === 'executed' ? 'bg-emerald-50 text-emerald-800' : 'bg-slate-100 text-slate-600']"
    >
      {{ a.status === "executed" ? `✓ ${a.result}` : "You declined this. Nothing was done." }}
    </p>
  </article>
</template>
