<script setup lang="ts">
import { computed, nextTick, ref, useId } from "vue";
import SourceTag from "@/components/agent/SourceTag.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import CollapseTransition from "@/components/ui/CollapseTransition.vue";
import IconTile from "@/components/ui/IconTile.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { t, tn } from "@/i18n";
import type { ContractSummary } from "@/types/api";
import { fmtDate } from "@/utils/format";
import ContractWarnings from "./ContractWarnings.vue";
import { ROLE, initialOf, partyOf, roleOf } from "./contracts";

/**
 * One contract in the list, read left to right: who it is with → what it is → supplier/customer, since when,
 * how many clauses Avida can quote, where it came from. Contracts the owner uploaded also show what to
 * double-check and can be removed – only behind an inline "Remove this contract?" confirm, so a misclick
 * never deletes anything. The parent does the API call (`remove`) and passes `removing` / `error` back.
 * Layout: phones = tile | text, button below · sm+ = tile | text | button (top right).
 */
const props = defineProps<{ contract: ContractSummary; isNew?: boolean; removing?: boolean; error?: string | null }>();
const emit = defineEmits<{ remove: [] }>();

const party = computed(() => partyOf(props.contract));
const role = computed(() => ROLE[roleOf(props.contract)]);
const uploaded = computed(() => props.contract.origin === "uploaded");
const cached = computed(() => props.contract.extracted_by === "cached answer");

const confirming = ref(false);
const panelId = useId();
const panel = ref<HTMLElement | null>(null);
const toggle = ref<InstanceType<typeof BaseButton> | null>(null);

async function askToRemove() {
  confirming.value = !confirming.value;
  if (!confirming.value) return;
  await nextTick();
  // safe default: focus lands on "Cancel", never on the destructive button
  panel.value?.querySelector<HTMLElement>("[data-cancel]")?.focus();
}

async function cancel() {
  if (props.removing) return;
  confirming.value = false;
  await nextTick();
  (toggle.value?.$el as HTMLElement | undefined)?.focus();
}
</script>

<template>
  <li class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 px-4 py-4 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:gap-x-4 sm:px-5">
    <IconTile tone="info" size="sm">{{ initialOf(contract) }}</IconTile>

    <div class="grid min-w-0 gap-1">
      <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
        <h3 class="min-w-0 break-words text-base font-bold leading-snug">{{ party }}</h3>
        <StatusPill v-if="isNew" tone="accent">{{ t("Just added") }}</StatusPill>
      </div>
      <p class="break-words text-label leading-snug text-muted">{{ contract.title }}</p>

      <ul class="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-2 text-label text-muted">
        <li class="inline-flex items-center gap-1.5 font-medium text-fg">
          <AppIcon :name="role.icon" :size="16" class="text-muted" />{{ t(role.label) }}
        </li>
        <li v-if="contract.start_date" class="inline-flex items-center gap-1.5">
          <AppIcon name="calendar" :size="16" />{{ t("Since {date}", { date: fmtDate(contract.start_date) }) }}
        </li>
        <li class="inline-flex items-center gap-1.5">
          <AppIcon name="listChecks" :size="16" />{{ tn(contract.clauses, "{n} key clause", "{n} key clauses") }}
        </li>
        <li class="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
          <StatusPill :tone="uploaded ? 'info' : 'neutral'">
            <AppIcon :name="uploaded ? 'sparkles' : 'document'" :size="14" />
            {{ !uploaded ? t("Added during setup") : cached ? t("Added by you") : t("Added by you · read by AI") }}
          </StatusPill>
          <!-- honest AI: the model was down, the terms come from a prepared copy -->
          <SourceTag v-if="uploaded && cached" source="fallback" />
        </li>
      </ul>

      <ContractWarnings v-if="contract.warnings?.length" :warnings="contract.warnings" class="mt-2" />
    </div>

    <BaseButton
      v-if="uploaded"
      ref="toggle"
      variant="ghost"
      icon="trash"
      class="col-start-2 mt-3 justify-self-start sm:col-start-3 sm:row-start-1 sm:mt-0 sm:self-start"
      :aria-label="t('Remove the contract with {party}', { party })"
      :aria-expanded="confirming"
      :aria-controls="panelId"
      @click="askToRemove"
    >
      {{ t("Remove") }}
    </BaseButton>

    <CollapseTransition>
      <div v-if="confirming" :id="panelId" ref="panel" class="col-start-2 sm:col-end-4" @keydown.esc="cancel">
        <div class="mt-3 grid gap-3 rounded-lg bg-negative-soft p-3.5" role="group" :aria-label="t('Remove this contract?')">
          <p class="flex items-start gap-2 font-semibold text-negative">
            <AppIcon name="trash" :size="18" class="mt-0.5" />
            {{ t("Remove this contract?") }}
          </p>
          <p class="text-label text-fg">
            {{ t("Avida will no longer use it to check your emails. You can add it again at any time.") }}
          </p>
          <div class="flex flex-wrap gap-2">
            <BaseButton variant="danger" icon="trash" :loading="removing" @click="emit('remove')">{{ t("Yes, remove") }}</BaseButton>
            <BaseButton variant="secondary" data-cancel :disabled="removing" @click="cancel">{{ t("Cancel") }}</BaseButton>
          </div>
          <p v-if="error" role="alert" class="flex items-start gap-2 text-label font-medium text-negative">
            <AppIcon name="alert" :size="16" class="mt-0.5" />
            <span class="min-w-0 break-words">{{ error }}</span>
          </p>
        </div>
      </div>
    </CollapseTransition>
  </li>
</template>
