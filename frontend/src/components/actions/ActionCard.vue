<script setup lang="ts">
import { computed, ref, watch } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import SourceTag from "@/components/agent/SourceTag.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import type { Action } from "@/types/api";
import { eur, eurCents, fmtDate } from "@/utils/format";

/**
 * One proposed action. UI rule #1: nothing happens without an explicit click on Approve / Not now.
 * Emits the decision; the parent (store) talks to the API.
 */
const props = defineProps<{ action: Action; busy?: boolean }>();
const emit = defineEmits<{ decide: [id: string, approve: boolean, editedBody?: string] }>();

const body = ref(props.action.type === "send_email" ? props.action.payload.body : "");
watch(
  () => props.action,
  (a) => {
    if (a.type === "send_email") body.value = a.payload.body;
  },
);

const pending = computed(() => props.action.status === "pending");
const approve = () => emit("decide", props.action.id, true, props.action.type === "send_email" ? body.value : undefined);
const decline = () => emit("decide", props.action.id, false);
</script>

<template>
  <article
    :class="[
      'grid gap-4 rounded-xl border bg-surface p-5',
      pending ? 'border-sun shadow-float' : 'border-line',
    ]"
  >
    <div class="flex flex-wrap items-center gap-2">
      <AutonomyBadge :level="action.autonomy" />
      <AutonomyBadge level="simulated" />
      <span class="text-sm text-muted">proposed by {{ action.agent }}</span>
      <SourceTag :source="action.source" />
    </div>

    <div class="grid gap-1.5">
      <h3 class="text-lg font-bold">{{ action.title }}</h3>
      <p><b>Why: </b>{{ action.why }}</p>
      <p v-if="action.savings_12m > 0" class="text-sm">
        Saves <b class="tabular-nums text-positive">{{ eur(action.savings_12m) }}</b> over the next 12 months.
      </p>
    </div>

    <!-- send_email: editable draft -->
    <label v-if="action.type === 'send_email'" class="grid gap-1.5">
      <span class="text-sm text-muted">
        Draft email to <b class="text-fg">{{ action.payload.to }}</b> – you can edit it before sending
      </span>
      <textarea
        v-model="body"
        :disabled="!pending"
        rows="10"
        class="w-full rounded-lg border border-line bg-input p-3 font-mono text-[0.85rem] leading-relaxed text-fg disabled:opacity-70"
      />
    </label>

    <!-- credit_application: offer details -->
    <div v-else class="grid gap-3 rounded-lg bg-input p-4">
      <dl class="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div><dt class="text-muted">Product</dt><dd class="font-semibold">{{ action.payload.product }}</dd></div>
        <div><dt class="text-muted">Amount</dt><dd class="font-semibold tabular-nums">{{ eur(action.payload.amount) }}</dd></div>
        <div>
          <dt class="text-muted">Needed</dt>
          <dd class="font-semibold">{{ fmtDate(action.payload.from) }} – {{ fmtDate(action.payload.until) }}</dd>
        </div>
        <div>
          <dt class="text-muted">Max. interest</dt>
          <dd class="font-semibold tabular-nums">{{ eurCents(action.payload.max_interest_cost) }} ({{ action.payload.indicative_rate_pct }} %)</dd>
        </div>
      </dl>
      <p class="text-sm text-muted">{{ action.payload.calculation }}</p>
      <p class="text-xs text-muted">{{ action.payload.bank }} · {{ action.payload.note }}</p>
    </div>

    <div v-if="pending" class="flex flex-wrap gap-3">
      <BaseButton size="lg" icon="check" :loading="busy" @click="approve">
        Approve {{ action.type === "send_email" ? "and send" : "and apply" }}
      </BaseButton>
      <BaseButton size="lg" variant="secondary" :disabled="busy" @click="decline">Not now</BaseButton>
    </div>
    <p
      v-else
      :class="[
        'flex items-start gap-2 rounded-lg p-3 font-semibold',
        action.status === 'executed' ? 'bg-positive-soft text-positive' : 'bg-input text-muted',
      ]"
      role="status"
    >
      <AppIcon :name="action.status === 'executed' ? 'checkCircle' : 'xCircle'" :size="18" class="mt-0.5" />
      {{ action.status === "executed" ? action.result : "You declined this. Nothing was done." }}
    </p>
  </article>
</template>
