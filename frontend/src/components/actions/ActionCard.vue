<script setup lang="ts">
import { computed, ref, watch } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import SourceTag from "@/components/agent/SourceTag.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import CollapseTransition from "@/components/ui/CollapseTransition.vue";
import StatTile from "@/components/ui/StatTile.vue";
import { t } from "@/i18n";
import type { Action } from "@/types/api";
import { eur, eurCents, fmtDayMonth } from "@/utils/format";
import RewriteDraft from "./RewriteDraft.vue";
import type { RewrittenDraft } from "./decision";

/**
 * One proposed action. UI rule #1: nothing happens without an explicit click on Approve / Not now.
 * Emits the decision; the parent (store) talks to the API.
 * `embedded`: rendered inside another card (Action center focus view) – no frame and no header of its own,
 *             the parent shows the title and badges.
 * `compact`:  also hides the "why" and the savings, for when the parent already explains them
 *             (the finding's email → contract → verdict flow).
 * Texts from the backend (title, why, draft, offer, result) are shown as delivered; the UI words are translated.
 * AV Rewrite (send_email, only when the parent listens – `rewritable`): the owner's wish goes out via `rewrite`,
 * the new text comes back as `rewritten` and replaces the editor content; "Undo" restores the text from before.
 */
const props = defineProps<{
  action: Action;
  busy?: boolean;
  compact?: boolean;
  embedded?: boolean;
  rewritable?: boolean;
  rewriting?: boolean;
  rewriteError?: string | null;
  rewritten?: RewrittenDraft | null;
}>();
const emit = defineEmits<{
  decide: [id: string, approve: boolean, editedBody?: string];
  rewrite: [id: string, body: string, instruction: string];
}>();

const body = ref(props.action.type === "send_email" ? props.action.payload.body : "");
watch(
  () => props.action,
  (a) => {
    if (a.type === "send_email") body.value = a.payload.body;
  },
);

const pending = computed(() => props.action.status === "pending");

/** The text before the last rewrite (for "Undo") and the source of the rewrite shown in the editor. */
const beforeRewrite = ref<string | null>(null);
const rewriteSource = ref<RewrittenDraft["source"] | null>(null);
watch(
  () => props.rewritten?.n,
  () => {
    if (!props.rewritten) return;
    beforeRewrite.value = body.value;
    body.value = props.rewritten.body;
    rewriteSource.value = props.rewritten.source;
  },
);
function undoRewrite() {
  if (beforeRewrite.value === null) return;
  body.value = beforeRewrite.value;
  beforeRewrite.value = null;
  rewriteSource.value = null;
}
const askRewrite = (instruction: string) => emit("rewrite", props.action.id, body.value, instruction);
const approve = () => emit("decide", props.action.id, true, props.action.type === "send_email" ? body.value : undefined);
const decline = () => emit("decide", props.action.id, false);
</script>

<template>
  <article
    :class="
      embedded
        ? 'grid gap-5'
        : [
            'grid gap-5 rounded-xl border bg-surface p-5 transition-colors duration-slow',
            pending ? 'border-sun' : 'border-line',
          ]
    "
  >
    <!-- one badge (autonomy) over the title, simulated / author / source as muted text · sm+: savings on the right -->
    <div v-if="!embedded" class="grid gap-3 sm:flex sm:items-start sm:gap-4">
      <div class="grid min-w-0 gap-2 sm:flex-1">
        <AutonomyBadge :level="action.autonomy" />
        <h3 class="text-xl font-semibold leading-snug">{{ action.title }}</h3>
        <p class="flex flex-wrap items-center gap-x-2 gap-y-1 text-label text-muted">
          <AutonomyBadge level="simulated" plain />
          <span aria-hidden="true">·</span>
          <span>{{ t("by {agent}", { agent: t(action.agent) }) }}</span>
          <SourceTag :source="action.source" />
        </p>
      </div>
      <!-- money you keep = green -->
      <div v-if="action.savings_12m > 0" class="hidden shrink-0 justify-items-end gap-1 leading-tight sm:grid">
        <span class="text-label text-muted">{{ t("You save") }}</span>
        <span class="font-display text-kpi font-semibold tracking-tight tabular-nums text-positive">{{ eur(action.savings_12m) }}</span>
        <span class="text-caption text-muted">{{ t("next 12 months") }}</span>
      </div>
    </div>

    <StatTile
      v-if="action.savings_12m > 0 && !compact"
      class="sm:hidden"
      icon="piggyBank"
      tone="positive"
      :label="t('You save (next 12 months)')"
      :value="eur(action.savings_12m)"
    />

    <p v-if="!compact" class="grid grid-cols-[auto_1fr] gap-2.5 leading-relaxed text-muted">
      <AppIcon name="recommendation" :size="20" class="mt-0.5 text-warn" />
      <span><b class="text-fg">{{ t("Why:") }} </b>{{ action.why }}</span>
    </p>

    <!-- four-eyes principle: the Legal Agent reviewed the Negotiator's draft (issues come from the backend as delivered) -->
    <div
      v-if="action.type === 'send_email' && action.review"
      :class="['grid gap-1.5 rounded-lg p-3 text-sm', action.review.approved ? 'bg-positive-soft text-positive' : 'bg-warn-soft text-warn']"
    >
      <p class="flex flex-wrap items-center gap-2 font-semibold">
        <AppIcon :name="action.review.approved ? 'checkCircle' : 'alert'" :size="18" />
        <template v-if="action.review.approved">
          {{
            action.review.rounds > 1
              ? t("Checked by {agent} – approved after one revision", { agent: t(action.reviewed_by ?? "Legal Agent") })
              : t("Checked by {agent} – approved", { agent: t(action.reviewed_by ?? "Legal Agent") })
          }}
        </template>
        <template v-else>{{ t("Checked by {agent} – please read it before sending", { agent: t(action.reviewed_by ?? "Legal Agent") }) }}</template>
      </p>
      <ul v-if="action.review.issues.length" class="grid gap-1 pl-7">
        <li v-for="i in action.review.issues" :key="i" class="list-disc">{{ i }}</li>
      </ul>
    </div>

    <!-- send_email: editable draft -->
    <div v-if="action.type === 'send_email'" class="grid gap-2">
      <label class="grid gap-2">
        <span class="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted">
          <AppIcon name="mail" :size="18" /> {{ t("To") }}
          <b class="min-w-0 text-fg [overflow-wrap:anywhere]">{{ action.payload.to }}</b>
          <Transition name="fade">
            <span v-if="pending" class="flex items-center gap-1 text-label">
              <AppIcon name="pencil" :size="14" /> {{ t("you can edit it") }}
            </span>
          </Transition>
        </span>
        <textarea
          v-model="body"
          :disabled="!pending"
          rows="8"
          :aria-busy="rewriting || undefined"
          :class="[
            'w-full rounded-lg border border-line bg-input p-3 font-mono text-sm leading-relaxed text-fg transition-opacity duration-base focus:border-fg/40 disabled:text-muted',
            rewriting ? 'opacity-60' : '',
          ]"
        />
      </label>
      <!-- after AV Rewrite: say so (honest about the AI) + one-click undo -->
      <CollapseTransition>
        <div v-if="pending && rewriteSource" role="status">
          <p class="flex flex-wrap items-center gap-x-2 gap-y-1 text-label text-muted">
            <AppIcon name="sparkles" :size="16" />
            <span>{{ t("Rewritten by Avida – please read it before sending.") }}</span>
            <SourceTag :source="rewriteSource" />
            <button
              v-if="beforeRewrite !== null"
              type="button"
              class="ml-auto flex min-h-10 items-center gap-1.5 rounded-lg px-2 font-semibold text-gold underline-offset-4 hover:underline"
              @click.prevent="undoRewrite"
            >
              <AppIcon name="undo" :size="16" />
              {{ t("Undo") }}
            </button>
          </p>
        </div>
      </CollapseTransition>
    </div>

    <!-- credit_application: offer details -->
    <div v-else class="grid gap-4 rounded-xl bg-input p-4">
      <p class="flex flex-wrap items-center gap-x-2">
        <b>{{ action.payload.product }}</b>
        <span class="text-muted">· {{ action.payload.bank }}</span>
      </p>
      <div class="grid gap-4 sm:grid-cols-3">
        <StatTile icon="euro" tone="info" :label="t('Amount')" :value="eur(action.payload.amount)" />
        <StatTile
          icon="calendar"
          tone="info"
          :label="t('Needed')"
          :value="`${fmtDayMonth(action.payload.from)} – ${fmtDayMonth(action.payload.until)}`"
        />
        <StatTile
          icon="landmark"
          tone="negative"
          :label="t('Max. interest')"
          :value="eurCents(action.payload.max_interest_cost)"
          :sub="t('{rate} % a year', { rate: action.payload.indicative_rate_pct })"
        />
      </div>
      <p class="text-label text-muted">{{ action.payload.calculation }} · {{ action.payload.note }}</p>
    </div>

    <!-- buttons → result: cross-fade, no jump -->
    <Transition name="rise" mode="out-in">
      <!--
        decision bar: the decision on the left (Approve / Not now), the helper on the right (AV Rewrite).
        Phones: everything stacked full width · sm+: one row, AV Rewrite pushed right; if it does not fit, it wraps
        to its own line (flex-wrap) – the buttons never overlap.
      -->
      <div v-if="pending" key="pending" class="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start">
        <div class="grid gap-3 sm:flex sm:flex-wrap">
          <BaseButton size="lg" icon="check" :loading="busy" :disabled="rewriting" @click="approve">
            {{ action.type === "send_email" ? t("Approve and send") : t("Approve and apply") }}
          </BaseButton>
          <BaseButton size="lg" variant="secondary" :disabled="busy" @click="decline">{{ t("Not now") }}</BaseButton>
        </div>
        <RewriteDraft
          v-if="rewritable && action.type === 'send_email'"
          class="sm:ml-auto"
          :busy="rewriting"
          :error="rewriteError"
          :disabled="busy"
          @submit="askRewrite"
        />
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
          {{ action.status === "executed" ? action.result : t("You declined this. Nothing was done.") }}
        </span>
      </p>
    </Transition>
  </article>
</template>
