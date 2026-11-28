<script setup lang="ts">
import { computed, ref } from "vue";
import ThinkingSpinner from "@/components/sync/ThinkingSpinner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import AppTooltip from "@/components/ui/AppTooltip.vue";
import { t, tn } from "@/i18n";
import type { ContractSummary } from "@/types/api";
import { fmtBytes, fmtDate } from "@/utils/format";
import { typeMeta, type SortKey, type SortState } from "./files";

/**
 * The contracts as a small file explorer (OneDrive-like): Name · Type · Added · Size · Actions.
 * - Click a column header to sort (again = reverse); `aria-sort` tells screen readers.
 * - Rows: generous height, a hairline between them and a full-row highlight on hover, so the eye keeps the line.
 * - Actions on the right: open (preview in a new tab), download, remove (only files the owner uploaded; the
 *   prepared ones are part of the demo data) – remove asks "Remove? Yes / Cancel" inline first.
 * - Drag & drop: dropping a file anywhere on the table uploads it; a dashed veil says "Drop to upload".
 * - Phones: Type / Added / Size move into the line under the name; the table never scrolls sideways.
 * Presentational: rows, sort and states in; `sort`, `remove`, `files` out. File links are plain URLs from `fileUrl`.
 */
const props = defineProps<{
  rows: ContractSummary[];
  sort: SortState;
  newId?: string | null;
  /** ids of the contracts being removed right now (several can be in flight) */
  removing?: readonly string[];
  removeError?: { id: string; message: string } | null;
  /** name of the file being read right now (10–20 s) – shown as a row on top */
  uploading?: string | null;
  /** link to the original file (preview inline, or `download`) – built by the parent from @/api */
  fileUrl: (id: string, download?: boolean) => string;
}>();
const emit = defineEmits<{ sort: [key: SortKey]; remove: [c: ContractSummary]; files: [files: FileList] }>();

const COLS: { key: SortKey; label: string; cls: string }[] = [
  { key: "name", label: "Name", cls: "text-left" },
  { key: "type", label: "Type", cls: "hidden w-24 text-left sm:table-cell" },
  { key: "date", label: "Added", cls: "hidden w-44 text-left md:table-cell" },
  { key: "size", label: "Size", cls: "hidden w-28 text-right sm:table-cell" },
];
const ariaSort = (k: SortKey) => (props.sort.key === k ? (props.sort.dir === "asc" ? "ascending" : "descending") : "none");

const added = (c: ContractSummary) => (c.uploaded_at ? fmtDate(c.uploaded_at) : t("Prepared by Avida"));

// --- remove: inline confirm -----------------------------------------------------------------------
const confirming = ref<string | null>(null);
const isRemoving = (id: string) => !!props.removing?.includes(id);
function confirmRemove(c: ContractSummary) {
  confirming.value = null;
  emit("remove", c);
}

// --- drag & drop ----------------------------------------------------------------------------------
const depth = ref(0);
const over = computed(() => depth.value > 0 && !props.uploading);
const hasFiles = (e: DragEvent) => !!e.dataTransfer && [...e.dataTransfer.types].includes("Files");
function onEnter(e: DragEvent) {
  if (hasFiles(e)) depth.value++;
}
function onLeave(e: DragEvent) {
  if (hasFiles(e)) depth.value = Math.max(0, depth.value - 1);
}
function onOver(e: DragEvent) {
  if (!hasFiles(e)) return;
  e.preventDefault();
  if (e.dataTransfer) e.dataTransfer.dropEffect = props.uploading ? "none" : "copy";
}
function onDrop(e: DragEvent) {
  if (!hasFiles(e)) return;
  e.preventDefault();
  depth.value = 0;
  if (!props.uploading && e.dataTransfer?.files.length) emit("files", e.dataTransfer.files);
}

const ACTION =
  "grid h-10 w-10 place-items-center rounded-lg text-muted transition-colors duration-fast hover:bg-surface hover:text-fg focus-visible:text-fg";
</script>

<template>
  <div
    :class="[
      'relative rounded-xl border bg-surface transition-colors duration-base',
      over ? 'border-fg/50' : 'border-line',
    ]"
    @dragenter="onEnter"
    @dragleave="onLeave"
    @dragover="onOver"
    @drop="onDrop"
  >
    <table class="w-full table-fixed border-collapse">
      <caption class="sr-only">{{ t("Your contract files") }}</caption>
      <thead>
        <tr class="border-b border-line">
          <th v-for="c in COLS" :key="c.key" scope="col" :aria-sort="ariaSort(c.key)" :class="['px-2 py-2 first:pl-4 sm:first:pl-5', c.cls]">
            <button
              type="button"
              :class="[
                'inline-flex min-h-10 items-center gap-1.5 rounded-lg px-2 text-sm font-semibold transition-colors duration-fast hover:bg-input/60',
                sort.key === c.key ? 'text-fg' : 'text-muted hover:text-fg',
                c.key === 'size' ? 'flex-row-reverse' : '',
              ]"
              @click="emit('sort', c.key)"
            >
              {{ t(c.label) }}
              <AppIcon
                :name="sort.key !== c.key ? 'arrowUpDown' : sort.dir === 'asc' ? 'chevronUp' : 'chevronDown'"
                :size="16"
                :class="sort.key === c.key ? '' : 'opacity-50'"
              />
            </button>
          </th>
          <th scope="col" class="w-[8.5rem] py-2 pr-4 text-right text-sm font-semibold text-muted sm:pr-5">
            <span class="px-2">{{ t("Actions") }}</span>
          </th>
        </tr>
      </thead>

      <tbody class="divide-y divide-line">
        <!-- the file being read right now -->
        <tr v-if="uploading" class="bg-input/40" aria-live="polite">
          <td colspan="5" class="px-4 py-4 sm:px-5">
            <span class="flex items-center gap-3">
              <ThinkingSpinner size="sm" />
              <span class="grid min-w-0 gap-0.5">
                <span class="truncate font-semibold">{{ uploading }}</span>
                <span class="text-label text-muted">{{ t("Avida is reading it. This takes 10–20 seconds.") }}</span>
              </span>
            </span>
          </td>
        </tr>

        <tr
          v-for="c in rows"
          :key="c.id"
          :class="['transition-colors duration-fast hover:bg-input/70', c.id === newId ? 'bg-positive-soft/40' : '']"
        >
          <!-- name: type icon · title · company (+ type / size / date on phones) -->
          <td class="py-3.5 pl-4 pr-2 sm:pl-5">
            <span class="flex min-w-0 items-center gap-3">
              <span class="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-input text-fg" aria-hidden="true">
                <AppIcon :name="typeMeta(c.file_type).icon" :size="20" />
              </span>
              <span class="grid min-w-0 gap-0.5">
                <span class="flex min-w-0 items-center gap-2">
                  <a
                    :href="fileUrl(c.id)"
                    target="_blank"
                    rel="noopener"
                    class="truncate font-semibold text-fg underline-offset-4 hover:underline"
                    :title="c.title"
                  >{{ c.title }}</a>
                  <span v-if="c.id === newId" class="shrink-0 rounded-md bg-positive-soft px-1.5 py-0.5 text-caption font-medium text-positive">
                    {{ t("New") }}
                  </span>
                  <AppTooltip
                    v-if="c.warnings_count"
                    :title="tn(c.warnings_count, '{n} thing to double-check', '{n} things to double-check')"
                    :text="t('The AI was unsure about some terms in this file. Compare them with the paper contract.')"
                    class="shrink-0"
                  >
                    <AppIcon name="alert" :size="18" class="text-warn" />
                  </AppTooltip>
                </span>
                <span class="truncate text-label text-muted">
                  {{ c.party }}
                  <span class="sm:hidden"> · {{ typeMeta(c.file_type).label }} · {{ fmtBytes(c.size_bytes) }}</span>
                  <span class="md:hidden"> · {{ added(c) }}</span>
                </span>
              </span>
            </span>
          </td>

          <!-- type -->
          <td class="hidden px-2 py-3.5 sm:table-cell">
            <span class="ml-2 inline-flex rounded-md border border-line bg-input px-2 py-0.5 text-caption font-semibold tracking-wide text-fg">
              {{ typeMeta(c.file_type).label }}
            </span>
          </td>

          <!-- added -->
          <td :class="['hidden px-2 py-3.5 md:table-cell', c.uploaded_at ? 'text-fg' : 'text-muted']">
            <span class="ml-2 text-sm tabular-nums">{{ added(c) }}</span>
          </td>

          <!-- size -->
          <td class="hidden px-2 py-3.5 text-right sm:table-cell">
            <span class="mr-2 text-sm tabular-nums">{{ fmtBytes(c.size_bytes) }}</span>
          </td>

          <!-- actions -->
          <td class="py-2 pr-4 sm:pr-5">
            <div v-if="confirming === c.id" class="flex items-center justify-end gap-1.5" role="group" :aria-label="t('Remove this contract?')">
              <button
                type="button"
                class="min-h-10 rounded-lg bg-negative px-3 text-sm font-semibold text-white hover:bg-negative/90"
                @click="confirmRemove(c)"
              >{{ t("Remove") }}</button>
              <button type="button" class="min-h-10 rounded-lg px-2 text-sm font-semibold text-muted hover:bg-surface hover:text-fg" @click="confirming = null">
                {{ t("Cancel") }}
              </button>
            </div>
            <div v-else class="flex items-center justify-end gap-0.5">
              <a :href="fileUrl(c.id)" target="_blank" rel="noopener" :class="ACTION" :title="t('Open')" :aria-label="t('Open {name}', { name: c.file_name })">
                <AppIcon name="eye" :size="18" />
              </a>
              <a :href="fileUrl(c.id, true)" :download="c.file_name" :class="ACTION" :title="t('Download')" :aria-label="t('Download {name}', { name: c.file_name })">
                <AppIcon name="download" :size="18" />
              </a>
              <button
                v-if="c.origin === 'uploaded'"
                type="button"
                :disabled="isRemoving(c.id)"
                :class="[ACTION, 'hover:text-negative disabled:opacity-50']"
                :title="t('Remove')"
                :aria-label="t('Remove {name}', { name: c.file_name })"
                @click="confirming = c.id"
              >
                <AppIcon :name="isRemoving(c.id) ? 'loader' : 'trash'" :size="18" :class="isRemoving(c.id) ? 'animate-spin' : ''" />
              </button>
              <AppTooltip v-else :text="t('Prepared contracts belong to the demo and cannot be removed.')">
                <span :class="[ACTION, 'cursor-help opacity-40 hover:bg-transparent']" aria-hidden="true">
                  <AppIcon name="trash" :size="18" />
                </span>
              </AppTooltip>
            </div>
            <p v-if="removeError?.id === c.id" class="mt-1 text-right text-label text-negative" role="alert">{{ removeError.message }}</p>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- nothing below the header: the parent's slot (empty states) -->
    <slot />

    <!-- drag & drop veil -->
    <Transition name="fade">
      <div
        v-if="over"
        class="pointer-events-none absolute inset-0 grid place-items-center rounded-xl border-2 border-dashed border-fg/50 bg-surface/90"
      >
        <span class="grid justify-items-center gap-2 text-center">
          <AppIcon name="cloudUpload" :size="36" class="text-fg" />
          <span class="text-lg font-semibold">{{ t("Drop the file to upload it") }}</span>
          <span class="text-label text-muted">{{ t("PDF, .md or .txt · up to 5 MB") }}</span>
        </span>
      </div>
    </Transition>
  </div>
</template>
