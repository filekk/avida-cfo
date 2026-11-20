<script setup lang="ts">
import { computed, ref, watch } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import SourceTag from "@/components/agent/SourceTag.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import IconTile from "@/components/ui/IconTile.vue";
import StatTile from "@/components/ui/StatTile.vue";
import type { Action } from "@/types/api";
import { eur, eurCents, fmtDayMonth } from "@/utils/format";

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
      'grid gap-5 rounded-xl border bg-surface p-5 transition-[border-color,box-shadow] duration-slow',
      pending ? 'border-sun shadow-float' : 'border-line shadow-card',
    ]"
  >
    <!-- mobile: tile + badges side by side, title full width below · sm+: tile | badges+title | savings -->
    <div class="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-4 gap-y-3 sm:flex sm:items-start">
      <IconTile
        :icon="action.type === 'send_email' ? 'send' : 'landmark'"
        :tone="pending ? 'accent' : 'neutral'"
        size="lg"
        class="transition-colors duration-slow"
      />
      <div class="contents sm:grid sm:min-w-0 sm:flex-1 sm:gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <AutonomyBadge :level="action.autonomy" />
          <AutonomyBadge level="simulated" />
          <span class="text-label text-muted">by {{ action.agent }}</span>
          <SourceTag :source="action.source" />
        </div>
        <h3 class="col-span-2 text-xl font-bold leading-snug sm:col-span-1">{{ action.title }}</h3>
      </div>
      <!-- money you keep = green -->
      <div v-if="action.savings_12m > 0" class="hidden shrink-0 justify-items-end gap-1 leading-tight sm:grid">
        <span class="text-label text-muted">You save</span>
        <span class="font-display text-kpi font-extrabold tabular-nums text-positive">{{ eur(action.savings_12m) }}</span>
        <span class="text-caption text-muted">next 12 months</span>
      </div>
    </div>

    <StatTile
      v-if="action.savings_12m > 0"
      class="sm:hidden"
      icon="piggyBank"
      tone="positive"
      label="You save (next 12 months)"
      :value="eur(action.savings_12m)"
    />

    <p class="grid grid-cols-[auto_1fr] gap-2.5 leading-relaxed text-muted">
      <AppIcon name="recommendation" :size="20" class="mt-0.5 text-warn" />
      <span><b class="text-fg">Why: </b>{{ action.why }}</span>
    </p>

    <!-- send_email: editable draft -->
    <label v-if="action.type === 'send_email'" class="grid gap-2">
      <span class="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted">
        <AppIcon name="mail" :size="18" /> To <b class="min-w-0 text-fg [overflow-wrap:anywhere]">{{ action.payload.to }}</b>
        <Transition name="fade">
          <span v-if="pending" class="flex items-center gap-1 text-label"><AppIcon name="pencil" :size="14" /> you can edit it</span>
        </Transition>
      </span>
      <textarea
        v-model="body"
        :disabled="!pending"
        rows="8"
        class="w-full rounded-lg border border-line bg-input p-3 font-mono text-sm leading-relaxed text-fg focus:border-fg/40 disabled:text-muted"
      />
    </label>

    <!-- credit_application: offer details -->
    <div v-else class="grid gap-4 rounded-xl bg-input p-4">
      <p class="flex flex-wrap items-center gap-x-2">
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
          tone="negative"
          label="Max. interest"
          :value="eurCents(action.payload.max_interest_cost)"
          :sub="`${action.payload.indicative_rate_pct} % a year`"
        />
      </div>
      <p class="text-label text-muted">{{ action.payload.calculation }} · {{ action.payload.note }}</p>
    </div>

    <!-- buttons → result: cross-fade, no jump -->
    <Transition name="rise" mode="out-in">
      <div v-if="pending" key="pending" class="grid gap-3 sm:flex sm:flex-wrap">
        <BaseButton size="lg" icon="check" :loading="busy" @click="approve">
          Approve {{ action.type === "send_email" ? "and send" : "and apply" }}
        </BaseButton>
        <BaseButton size="lg" variant="secondary" :disabled="busy" @click="decline">Not now</BaseButton>
      </div>
      <p
        v-else
        key="decided"
        :class="[
          'flex items-start gap-2.5 rounded-lg p-3.5 font-semibold',
          action.status === 'executed' ? 'bg-positive-soft text-positive' : 'bg-input text-muted',
        ]"
        role="status"
      >
        <AppIcon :name="action.status === 'executed' ? 'checkCircle' : 'xCircle'" :size="20" class="mt-0.5" />
        <span class="min-w-0 [overflow-wrap:anywhere]">
          {{ action.status === "executed" ? action.result : "You declined this. Nothing was done." }}
        </span>
      </p>
    </Transition>
  </article>
</template>
