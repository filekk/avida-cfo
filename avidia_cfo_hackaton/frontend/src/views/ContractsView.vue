<script setup lang="ts">
import { computed, ref } from "vue";
import { ApiError, CONTRACT_ACCEPT, contractFileUrl, deleteContract, errorMessage, getContracts, uploadContract } from "@/api";
import ContractTable from "@/components/contracts/ContractTable.vue";
import ContractsToolbar from "@/components/contracts/ContractsToolbar.vue";
import UploadSummary from "@/components/contracts/UploadSummary.vue";
import { partyOf } from "@/components/contracts/contracts";
import {
  DEFAULT_SORT,
  FILE_TYPES,
  NO_FILTERS,
  applyFilters,
  applySort,
  isFiltered,
  nextSort,
  validateFile,
  type FileFilters,
  type SortKey,
  type SortState,
} from "@/components/contracts/files";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { useAsyncData } from "@/composables/useAsyncData";
import { t } from "@/i18n";
import type { ContractSummary, UploadResult } from "@/types/api";

/**
 * Contracts = a small file explorer (OneDrive-like) of the contracts the Legal Agent checks every price change and
 * late payment against:
 *   header with the ONE main button "Upload contract" → toolbar (search, type, added, size) → table
 *   (Name · Type · Added · Size · Actions, sortable headers). Files can also be dropped onto the table.
 * Filtering and sorting happen here in the browser (the list is small); the backend's filters are not needed.
 * An upload is read live by the model (10–20 s) and counts from the next inbox check.
 */
const { data: contracts, loading, error, reload, set: setContracts } = useAsyncData(getContracts);
const list = computed(() => contracts.value ?? []);

// --- filters + sort --------------------------------------------------------------------------------
const filters = ref<FileFilters>({ ...NO_FILTERS });
const sort = ref<SortState>({ ...DEFAULT_SORT });
const rows = computed(() => applySort(applyFilters(list.value, filters.value), sort.value));
/** Type chips: what can be uploaded + anything else that is already in the list. */
const types = computed(() => [...new Set<string>([...FILE_TYPES, ...list.value.map((c) => c.file_type)])]);
const clearFilters = () => (filters.value = { ...NO_FILTERS });
const onSort = (k: SortKey) => (sort.value = nextSort(sort.value, k));

// --- upload --------------------------------------------------------------------------------------
const input = ref<HTMLInputElement | null>(null);
const uploading = ref<string | null>(null);
const uploadError = ref<{ message: string; detail?: string } | null>(null);
const last = ref<UploadResult | null>(null);
const newId = ref<string | null>(null);
/** Screen-reader announcements (one persistent live region, so every change is read out). */
const announcement = ref("");

function pick() {
  input.value?.click();
}
function onPicked(e: Event) {
  const el = e.target as HTMLInputElement;
  if (el.files?.length) take(el.files);
  el.value = ""; // the same file can be picked again
}

/** From the button or a drop: one file at a time, checked before sending. */
function take(files: FileList) {
  const f = files[0];
  if (!f || uploading.value) return;
  const problem = validateFile(f);
  if (problem) {
    last.value = null;
    uploadError.value = { message: problem };
    return;
  }
  upload(f);
}

async function upload(file: File) {
  uploading.value = file.name;
  uploadError.value = null;
  last.value = null;
  announcement.value = t("Reading your contract. This takes 10–20 seconds.");
  try {
    const res = await uploadContract(file);
    last.value = res;
    newId.value = res.contract.id;
    announcement.value = t("Contract added: {party}", { party: partyOf(res.contract) });
    // the new file must be visible: drop filters that would hide it
    if (isFiltered(filters.value)) clearFilters();
    await reload();
  } catch (e) {
    // server answers (422 unreadable, model down…): plain lead + the backend's reason as delivered
    uploadError.value =
      e instanceof ApiError && e.status > 0
        ? { message: t("Avida could not read this file."), detail: e.message }
        : { message: errorMessage(e) };
    announcement.value = "";
  } finally {
    uploading.value = null;
  }
}

// --- remove (only after the row's inline "Remove" confirm) ---------------------------------------
/** Several removals can be in flight; each row stays disabled until its own request is done. */
const removing = ref<string[]>([]);
const removeError = ref<{ id: string; message: string } | null>(null);
let removeRun = 0;
async function remove(c: ContractSummary) {
  if (removing.value.includes(c.id)) return;
  const mine = ++removeRun;
  removing.value = [...removing.value, c.id];
  removeError.value = null;
  try {
    const next = await deleteContract(c.id);
    // only the newest removal's list is complete – an older answer would bring a just-removed row back
    if (mine === removeRun) setContracts(next);
    if (last.value?.contract.id === c.id) last.value = null;
    if (newId.value === c.id) newId.value = null;
    announcement.value = t("Contract removed: {party}", { party: partyOf(c) });
  } catch (e) {
    removeError.value = { id: c.id, message: errorMessage(e) };
  } finally {
    removing.value = removing.value.filter((id) => id !== c.id);
  }
}
</script>

<template>
  <div class="grid grid-cols-[minmax(0,1fr)] gap-5">
    <PageHeader
      :title="t('Your contracts')"
      :description="
        t(
          'When a supplier raises prices or a customer pays late, Avida checks it against these contracts. A contract you add counts from the next inbox check.',
        )
      "
    >
      <BaseButton icon="cloudUpload" :loading="!!uploading" @click="pick">{{ t("Upload contract") }}</BaseButton>
      <input ref="input" type="file" class="sr-only" tabindex="-1" aria-hidden="true" :accept="CONTRACT_ACCEPT" @change="onPicked" />
    </PageHeader>

    <!-- upload feedback: what went wrong, or what Avida read from the new contract -->
    <AlertBanner v-if="uploadError" dismissible @dismiss="uploadError = null">
      <span class="grid gap-1">
        <span>{{ uploadError.message }}</span>
        <span v-if="uploadError.detail" class="break-words text-label font-normal">{{ uploadError.detail }}</span>
      </span>
    </AlertBanner>
    <Transition name="rise">
      <UploadSummary v-if="last" :result="last" @close="last = null" />
    </Transition>

    <AlertBanner v-if="error">
      {{ error }} <button type="button" class="ml-2 underline" @click="reload">{{ t("Try again") }}</button>
    </AlertBanner>

    <!-- loading: same toolbar + row shapes as the real list → nothing jumps -->
    <BaseCard v-if="loading && !contracts" aria-busy="true">
      <div class="grid gap-3">
        <SkeletonBlock height="h-11" class="w-full sm:w-96" />
        <SkeletonBlock v-for="i in 4" :key="i" height="h-14" />
      </div>
    </BaseCard>

    <template v-else-if="contracts">
      <ContractsToolbar v-model="filters" :types="types" :shown="rows.length" :total="list.length" @clear="clearFilters" />

      <ContractTable
        :rows="rows"
        :sort="sort"
        :new-id="newId"
        :removing="removing"
        :remove-error="removeError"
        :uploading="uploading"
        :file-url="contractFileUrl"
        @sort="onSort"
        @remove="remove"
        @files="take"
      >
        <!-- empty: no file matches the filters / no contracts at all -->
        <div v-if="!rows.length && !uploading" class="grid justify-items-center gap-3 px-4 py-12 text-center">
          <span class="grid h-12 w-12 place-items-center rounded-xl bg-input text-muted" aria-hidden="true">
            <AppIcon :name="list.length ? 'search' : 'cloudUpload'" :size="24" />
          </span>
          <template v-if="list.length">
            <p class="text-lg font-semibold">{{ t("No file matches your filters") }}</p>
            <p class="max-w-md text-label text-muted">{{ t("Try another name, or show all files again.") }}</p>
            <BaseButton variant="secondary" icon="x" @click="clearFilters">{{ t("Clear filters") }}</BaseButton>
          </template>
          <template v-else>
            <p class="text-lg font-semibold">{{ t("No contracts yet") }}</p>
            <p class="max-w-md text-label text-muted">
              {{ t("Upload your first contract or drop the file here. Avida then checks price changes and late payments against it.") }}
            </p>
          </template>
        </div>
      </ContractTable>

      <p class="flex items-center gap-2 text-label text-muted">
        <AppIcon name="info" :size="16" class="shrink-0" />
        {{ t("Tip: drag a file from your computer onto the table to upload it. PDF, .md or .txt, up to 5 MB.") }}
      </p>
    </template>

    <p class="sr-only" role="status">{{ announcement }}</p>
  </div>
</template>
