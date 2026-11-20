<script setup lang="ts">
import { computed, ref, watch } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import SourceTag from "@/components/agent/SourceTag.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import StatTile from "@/components/ui/StatTile.vue";
import type { Action } from "@/types/api";
import { eur, eurCents, fmtDayMonth } from "@/utils/format";

/**
 * One proposed action. UI rule #1: nothing happens without an explicit click on Approve / Not now.
 * Emits the decision; the parent (store) talks to the API.
 */
/**
 * `embedded`: rendered inside another card (Action center row) – no frame and no header of its own,
 *             the parent shows the title and badges.
 * `compact`:  also hides the "why" and the savings, for when the parent already explains them
 *             (the finding's email → contract → verdict flow).
 */
const props = defineProps<{ action: Action; busy?: boolean; compact?: boolean; embedded?: boolean }>();
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
    :class="
      embedded
        ? 'grid gap-5'
        : ['grid gap-5 rounded-xl border bg-surface p-5', pending ? 'border-sun shadow-float' : 'border-line']
    "
  >
    <div v-if="!embedded" class="flex items-start gap-4">
      <span
        :class="['grid h-12 w-12 shrink-0 place-items-center rounded-xl', pending ? 'bg-sun text-sun-on' : 'bg-input text-muted']"
        aria-hidden="true"
      >
        <AppIcon :name="action.type === 'send_email' ? 'send' : 'landmark'" :size="22" />
      </span>
      <div class="grid min-w-0 flex-1 gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <AutonomyBadge :level="action.autonomy" />
          <AutonomyBadge level="simulated" />
          <span class="text-[0.8rem] text-muted">by {{ action.agent }}</span>
          <SourceTag :source="action.source" />
        </div>
        <h3 class="text-lg font-bold leading-snug">{{ action.title }}</h3>
      </div>
      <div v-if="action.savings_12m > 0 && !compact" class="hidden shrink-0 justify-items-end leading-tight sm:grid">
        <span class="text-[0.78rem] text-muted">You save</span>
        <span class="font-display text-2xl font-extrabold tabular-nums text-positive">{{ eur(action.savings_12m) }}</span>
        <span class="text-[0.75rem] text-muted">next 12 months</span>
      </div>
    </div>

    <StatTile
      v-if="action.savings_12m > 0 && !compact"
      class="sm:hidden"
      icon="piggyBank"
      tone="positive"
      label="You save (next 12 months)"
      :value="eur(action.savings_12m)"
    />

    <p v-if="!compact" class="grid grid-cols-[auto_1fr] gap-2 text-sm leading-relaxed text-muted">
      <AppIcon name="recommendation" :size="17" class="mt-0.5 text-warn" />
      <span><b class="text-fg">Why: </b>{{ action.why }}</span>
    </p>

    <!-- send_email: editable draft -->
    <label v-if="action.type === 'send_email'" class="grid gap-2">
      <span class="flex flex-wrap items-center gap-2 text-sm text-muted">
        <AppIcon name="mail" /> To <b class="text-fg">{{ action.payload.to }}</b>
        <span v-if="pending" class="flex items-center gap-1 text-[0.8rem]"><AppIcon name="pencil" :size="13" /> you can edit it</span>
      </span>
      <textarea
        v-model="body"
        :disabled="!pending"
        rows="8"
        class="w-full rounded-lg border border-line bg-input p-3 font-mono text-[0.85rem] leading-relaxed text-fg disabled:opacity-70"
      />
    </label>

    <!-- credit_application: offer details -->
    <div v-else class="grid gap-4 rounded-xl bg-input/70 p-4">
      <p class="flex flex-wrap items-center gap-x-2 text-sm">
        <b>{{ action.payload.product }}</b>
        <span class="text-muted">· {{ action.payload.bank }}</span>
      </p>
      <div class="grid gap-4 sm:grid-cols-3">
        <StatTile icon="euro" tone="info" label="Amount" :value="eur(action.payload.amount)" />
        <StatTile
          icon="calendar"
          tone="info"
          label="Needed"
          :value="`${fmtDayMonth(action.payload.from)} – ${fmtDayMonth(action.payload.until)}`"
        />
        <StatTile
          icon="landmark"
          tone="info"
          label="Max. interest"
          :value="eurCents(action.payload.max_interest_cost)"
          :sub="`${action.payload.indicative_rate_pct} % a year`"
        />
      </div>
      <p class="text-[0.8rem] text-muted">{{ action.payload.calculation }} · {{ action.payload.note }}</p>
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
