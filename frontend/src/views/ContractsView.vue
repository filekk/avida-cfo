<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import { ApiError, CONTRACT_ACCEPT, CONTRACT_MAX_BYTES, deleteContract, getContracts, uploadContract } from "@/api";
import ContractRow from "@/components/contracts/ContractRow.vue";
import ContractUpload from "@/components/contracts/ContractUpload.vue";
import UploadSummary from "@/components/contracts/UploadSummary.vue";
import { ROLE, partyOf, roleOf, rowCleanup, rowEnter, rowLeave } from "@/components/contracts/contracts";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { useAsyncData } from "@/composables/useAsyncData";
import { t, tn } from "@/i18n";
import type { ContractSummary, UploadResult } from "@/types/api";
import { prefersReducedMotion } from "@/utils/motion";

/**
 * The contracts the Legal Agent checks every price change and late payment against, plus adding a new one.
 * Order = what the owner needs first: the list (what protects me) on the left / on top, "Add a contract" on the
 * right / below. Two columns only when the PAGE is wide enough (container query in rem, so large text sizes
 * fall back to one column); in one column the header button opens the file picker and scrolls to the box.
 * An upload is read live by the model (10–20 s) and used from the next inbox check.
 */
const { data: contracts, loading, error, reload } = useAsyncData(getContracts);
const list = computed(() => contracts.value ?? []);
const counts = computed(() => ({
  supplier: list.value.filter((c) => roleOf(c) === "supplier").length,
  customer: list.value.filter((c) => roleOf(c) === "customer").length,
}));

const uploading = ref(false);
const uploadError = ref<{ message: string; detail?: string } | null>(null);
const last = ref<UploadResult | null>(null);
const newId = ref<string | null>(null);
const removing = ref<string | null>(null);
const removeError = ref<{ id: string; message: string } | null>(null);
/** Screen-reader announcements (one persistent live region, so every change is read out). */
const announcement = ref("");

const uploadCard = ref<InstanceType<typeof BaseCard> | null>(null);
const picker = ref<InstanceType<typeof ContractUpload> | null>(null);
const listEl = ref<{ $el: HTMLElement } | null>(null);

const messageOf = (e: unknown) => (e instanceof Error ? e.message : t("Something went wrong."));

/** Header / empty-state button: bring the upload box into view and open the file picker. */
function addContract() {
  (uploadCard.value?.$el as HTMLElement | undefined)?.scrollIntoView({
    behavior: prefersReducedMotion() ? "auto" : "smooth",
    block: "start",
  });
  picker.value?.open();
}

function invalid(message: string) {
  last.value = null;
  uploadError.value = { message };
}

async function upload(file: File) {
  uploading.value = true;
  uploadError.value = null;
  last.value = null;
  announcement.value = t("Reading your contract. This takes 10–20 seconds.");
  try {
    const res = await uploadContract(file);
    last.value = res;
    newId.value = res.contract.id;
    announcement.value = t("Contract added: {party}", { party: partyOf(res.contract) });
    await reload();
  } catch (e) {
    // server answers (422 unreadable, model down…): plain lead + the backend's reason as delivered
    uploadError.value =
      e instanceof ApiError && e.status > 0
        ? { message: t("Avida could not read this file."), detail: e.message }
        : { message: messageOf(e) };
    announcement.value = "";
  } finally {
    uploading.value = false;
  }
}

/** Owner action – only from the click on "Yes, remove" in the row's confirm. */
async function remove(c: ContractSummary) {
  removing.value = c.id;
  removeError.value = null;
  try {
    contracts.value = await deleteContract(c.id);
    if (last.value?.contract.id === c.id) last.value = null;
    if (newId.value === c.id) newId.value = null;
    announcement.value = t("Contract removed: {party}", { party: partyOf(c) });
    // the focused button is gone → keep keyboard users in the list
    await nextTick();
    listEl.value?.$el.focus();
  } catch (e) {
    removeError.value = { id: c.id, message: messageOf(e) };
  } finally {
    removing.value = null;
  }
}
</script>

<template>
  <div class="grid grid-cols-[minmax(0,1fr)] gap-5 [container-type:inline-size]">
    <PageHeader
      :title="t('Your contracts')"
      :description="
        t(
          'When a supplier raises prices or a customer pays late, Avida checks it against these contracts. A contract you add counts from the next inbox check.',
        )
      "
    >
      <BaseButton variant="secondary" icon="plus" :disabled="uploading" class="[@container(min-width:52rem)]:hidden" @click="addContract">
        {{ t("Add a contract") }}
      </BaseButton>
    </PageHeader>

    <div class="grid items-start gap-5 [@container(min-width:52rem)]:grid-cols-[minmax(0,1fr)_21rem]">
      <!-- 1. what protects you: the contracts Avida checks against -->
      <div class="grid min-w-0 gap-5">
        <AlertBanner v-if="error">
          {{ error }} <button type="button" class="ml-2 underline" @click="reload">{{ t("Try again") }}</button>
        </AlertBanner>

        <!-- loading: same card, header and row shapes as the real list → nothing jumps when it arrives -->
        <BaseCard v-if="loading && !contracts" :title="t('Contracts Avida knows')" :padded="false" aria-busy="true">
          <ul class="divide-y divide-line border-t border-line">
            <li v-for="i in 4" :key="i" class="flex gap-3 px-4 py-4 sm:gap-4 sm:px-5">
              <SkeletonBlock height="h-10" class="w-10 shrink-0" />
              <div class="grid flex-1 gap-2 pt-0.5">
                <SkeletonBlock height="h-5" class="w-2/5" />
                <SkeletonBlock height="h-4" class="w-4/5" />
                <SkeletonBlock height="h-6" class="mt-1 w-3/5" />
              </div>
            </li>
          </ul>
        </BaseCard>

        <BaseCard v-else-if="list.length" :title="t('Contracts Avida knows')" :padded="false">
          <template #actions>
            <StatusPill v-if="counts.supplier" tone="neutral">
              <AppIcon :name="ROLE.supplier.icon" :size="14" />{{ tn(counts.supplier, "{n} supplier", "{n} suppliers") }}
            </StatusPill>
            <StatusPill v-if="counts.customer" tone="neutral">
              <AppIcon :name="ROLE.customer.icon" :size="14" />{{ tn(counts.customer, "{n} customer", "{n} customers") }}
            </StatusPill>
          </template>
          <TransitionGroup
            ref="listEl"
            tag="ul"
            :css="false"
            class="divide-y divide-line border-t border-line focus:outline-none"
            tabindex="-1"
            :aria-label="t('Contracts Avida knows')"
            @enter="rowEnter"
            @after-enter="rowCleanup"
            @leave="rowLeave"
            @after-leave="rowCleanup"
          >
            <ContractRow
              v-for="c in list"
              :key="c.id"
              :contract="c"
              :is-new="c.id === newId"
              :removing="removing === c.id"
              :error="removeError?.id === c.id ? removeError.message : null"
              @remove="remove(c)"
            />
          </TransitionGroup>
        </BaseCard>

        <EmptyState
          v-else-if="!error"
          icon="document"
          :title="t('No contracts yet')"
          :description="t('Add your first contract. Avida then checks price changes and late payments against it.')"
        >
          <BaseButton variant="secondary" icon="plus" :disabled="uploading" @click="addContract">{{ t("Add a contract") }}</BaseButton>
        </EmptyState>
      </div>

      <!-- 2. add a new one -->
      <BaseCard ref="uploadCard" :title="t('Add a contract')" class="scroll-mt-32">
        <div class="grid gap-4">
          <p class="-mt-1 text-label text-muted">
            {{ t("Avida reads it and picks out what matters: prices, notice periods and payment terms.") }}
          </p>
          <ContractUpload
            ref="picker"
            :busy="uploading"
            :accept="CONTRACT_ACCEPT"
            :max-bytes="CONTRACT_MAX_BYTES"
            @file="upload"
            @invalid="invalid"
          />
          <AlertBanner v-if="uploadError" dismissible @dismiss="uploadError = null">
            <span class="grid gap-1">
              <span>{{ uploadError.message }}</span>
              <span v-if="uploadError.detail" class="break-words text-label font-normal">{{ uploadError.detail }}</span>
            </span>
          </AlertBanner>
          <Transition name="rise">
            <UploadSummary v-if="last" :result="last" @close="last = null" />
          </Transition>
        </div>
      </BaseCard>
    </div>

    <p class="sr-only" role="status">{{ announcement }}</p>
  </div>
</template>
