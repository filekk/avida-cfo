<script setup lang="ts">
import { computed, ref } from "vue";
import { ApiError, CONTRACT_ACCEPT, CONTRACT_MAX_BYTES, deleteContract, getContracts, uploadContract } from "@/api";
import SourceTag from "@/components/agent/SourceTag.vue";
import ContractUpload from "@/components/contracts/ContractUpload.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import IconTile from "@/components/ui/IconTile.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { useAsyncData } from "@/composables/useAsyncData";
import { t, tn } from "@/i18n";
import type { ContractSummary, UploadResult } from "@/types/api";
import { fmtDate } from "@/utils/format";

/**
 * The Legal Agent's knowledge base: contracts prepared in the Jupyter workbench + contracts the owner uploads.
 * An upload is read live by Granite (guided JSON, every quote checked word for word) and used on the next inbox check.
 */
const { data: contracts, loading, error, reload } = useAsyncData(getContracts);

const uploading = ref(false);
const uploadError = ref<string | null>(null);
const last = ref<UploadResult | null>(null);
const removing = ref<string | null>(null);

const party = (c: { supplier?: string; customer?: string }) => c.supplier ?? c.customer ?? "–";
const sorted = computed(() => contracts.value ?? []);

async function upload(file: File) {
  uploading.value = true;
  uploadError.value = null;
  last.value = null;
  try {
    last.value = await uploadContract(file);
    await reload();
  } catch (e) {
    uploadError.value = e instanceof ApiError || e instanceof Error ? e.message : t("Something went wrong.");
  } finally {
    uploading.value = false;
  }
}

/** Owner action – only from the click on "Remove". */
async function remove(c: ContractSummary) {
  removing.value = c.id;
  uploadError.value = null;
  try {
    contracts.value = await deleteContract(c.id);
    if (last.value?.contract.id === c.id) last.value = null;
  } catch (e) {
    uploadError.value = e instanceof ApiError || e instanceof Error ? e.message : t("Something went wrong.");
  } finally {
    removing.value = null;
  }
}
</script>

<template>
  <PageHeader
    :eyebrow="t('Legal Agent')"
    :title="t('Your contracts')"
    :description="t('The Legal Agent checks every change against these contracts. Add a new one and it is used on the next inbox check.')"
  />

  <BaseCard :title="t('Add a contract')">
    <div class="grid gap-4">
      <ContractUpload
        :busy="uploading"
        :accept="CONTRACT_ACCEPT"
        :max-bytes="CONTRACT_MAX_BYTES"
        @file="upload"
        @invalid="(m) => (uploadError = m)"
      />

      <AlertBanner v-if="uploadError" dismissible @dismiss="uploadError = null">{{ uploadError }}</AlertBanner>

      <Transition name="rise">
        <div v-if="last" class="grid gap-3 rounded-xl bg-positive-soft p-4" role="status">
          <p class="flex flex-wrap items-center gap-x-2 gap-y-1 font-semibold text-positive">
            <AppIcon name="checkCircle" :size="20" />
            {{ t("Read: {title}", { title: last.contract.title }) }}
            <SourceTag :source="last.source" />
          </p>
          <p class="text-sm">
            {{
              t("Other party: {party} · {clauses} · {pages} · {seconds} s", {
                party: party(last.contract),
                clauses: tn(last.contract.clauses.length, "{n} clause", "{n} clauses"),
                pages: tn(last.pages, "{n} page", "{n} pages"),
                seconds: last.seconds,
              })
            }}
          </p>
          <p class="text-sm">{{ t("Run the inbox check again – the Legal Agent will use this contract.") }}</p>
          <ul v-if="last.contract.warnings.length" class="grid gap-1.5 rounded-lg bg-warn-soft p-3 text-sm text-warn">
            <li class="font-semibold">{{ t("Please double-check:") }}</li>
            <li v-for="w in last.contract.warnings" :key="w" class="flex items-start gap-2">
              <AppIcon name="alert" :size="16" class="mt-0.5" /> {{ w }}
            </li>
          </ul>
        </div>
      </Transition>
    </div>
  </BaseCard>

  <AlertBanner v-if="error">
    {{ error }} <button type="button" class="ml-2 underline" @click="reload">{{ t("Try again") }}</button>
  </AlertBanner>
  <SkeletonBlock v-else-if="loading && !contracts" height="h-48" />

  <BaseCard v-else-if="sorted.length" :title="t('Contracts the Legal Agent knows')" :padded="false">
    <ul class="divide-y divide-line">
      <li v-for="c in sorted" :key="c.id" class="grid gap-3 px-5 py-4 animate-rise sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center">
        <IconTile icon="document" :tone="c.origin === 'uploaded' ? 'info' : 'neutral'" size="sm" />
        <div class="grid min-w-0 gap-1">
          <b class="leading-snug [overflow-wrap:anywhere]">{{ c.title }}</b>
          <span class="flex flex-wrap items-center gap-x-2 gap-y-1 text-label text-muted">
            <span>{{ party(c) }}</span>
            <span>· {{ c.customer ? t("customer") : t("supplier") }}</span>
            <span v-if="c.start_date">· {{ t("since {date}", { date: fmtDate(c.start_date) }) }}</span>
            <span>· {{ tn(c.clauses, "{n} clause", "{n} clauses") }}</span>
          </span>
          <span class="flex flex-wrap items-center gap-2">
            <StatusPill :tone="c.origin === 'uploaded' ? 'info' : 'neutral'">
              <AppIcon :name="c.origin === 'uploaded' ? 'sparkles' : 'listChecks'" :size="14" />
              {{
                c.origin !== "uploaded"
                  ? t("Prepared in the Jupyter workbench")
                  : c.extracted_by === "cached answer"
                    ? t("Uploaded by you · cached answer")
                    : t("Uploaded by you · terms read by the AI model")
              }}
            </StatusPill>
            <StatusPill v-if="c.warnings?.length" tone="warn">
              <AppIcon name="alert" :size="14" /> {{ tn(c.warnings.length, "{n} thing to check", "{n} things to check") }}
            </StatusPill>
          </span>
        </div>
        <BaseButton
          v-if="c.origin === 'uploaded'"
          variant="ghost"
          size="sm"
          icon="trash"
          :loading="removing === c.id"
          @click="remove(c)"
        >
          {{ t("Remove") }}
        </BaseButton>
      </li>
    </ul>
  </BaseCard>
  <EmptyState v-else icon="document" :title="t('No contracts yet')" :description="t('Upload your first contract above.')" />
</template>
