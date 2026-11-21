<script setup lang="ts">
import { computed, ref, useId } from "vue";
import ThinkingSpinner from "@/components/sync/ThinkingSpinner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import IconTile from "@/components/ui/IconTile.vue";
import { t } from "@/i18n";

/**
 * Drop zone + file picker for one contract (PDF / .md / .txt). Checks type and size before emitting, so the
 * owner gets an instant message instead of a 422 after the upload. The parent does the upload; `busy` shows the
 * "Avida is reading it" state (10–20 s).
 *   - The whole box is the <label>: a click or tap anywhere opens the picker (big touch target).
 *   - The input is visually hidden, so keyboard focus on it draws the focus ring on the box (`has-[:focus-visible]`).
 *   - Idle and busy content share one grid cell and cross-fade → the box never changes height.
 *   - Drag-over: a veil fades in on top ("Drop the file to add it"); dragenter/leave are counted because they
 *     fire for every child element.
 * `open()` lets the page's "Add a contract" button open the picker directly.
 */
const props = defineProps<{ busy?: boolean; accept: string; maxBytes: number }>();
const emit = defineEmits<{ file: [file: File]; invalid: [message: string] }>();

const input = ref<HTMLInputElement | null>(null);
const depth = ref(0);
const over = computed(() => depth.value > 0 && !props.busy);
const fileName = ref("");
const hintId = useId();

function take(files: FileList | null | undefined) {
  const f = files?.[0];
  if (!f || props.busy) return;
  const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();
  if (!props.accept.split(",").includes(ext)) return emit("invalid", t("Please choose a PDF or a text file (.txt, .md)."));
  if (f.size > props.maxBytes) return emit("invalid", t("This file is larger than 5 MB. Please choose a smaller one."));
  fileName.value = f.name;
  emit("file", f);
}

function onChange(e: Event) {
  const el = e.target as HTMLInputElement;
  take(el.files);
  el.value = ""; // the same file can be picked again
}

function onDragOver(e: DragEvent) {
  if (e.dataTransfer) e.dataTransfer.dropEffect = props.busy ? "none" : "copy";
}

function onDrop(e: DragEvent) {
  depth.value = 0;
  take(e.dataTransfer?.files);
}

defineExpose({ open: () => input.value?.click() });
</script>

<template>
  <label
    :class="[
      'group relative grid min-h-[14rem] place-items-center rounded-xl border-2 border-dashed p-5 text-center',
      'transition-[border-color,background-color] duration-base',
      'has-[:focus-visible]:border-solid has-[:focus-visible]:border-fg/50',
      'has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px] has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-sun',
      busy
        ? 'cursor-progress border-line bg-input/50'
        : over
          ? 'border-fg/60 bg-mist'
          : 'cursor-pointer border-line bg-input/50 hover:border-fg/40 hover:bg-mist/50',
    ]"
    :aria-busy="busy || undefined"
    @dragenter.prevent="depth++"
    @dragover.prevent="onDragOver"
    @dragleave="depth = Math.max(0, depth - 1)"
    @drop.prevent="onDrop"
  >
    <input
      ref="input"
      type="file"
      class="sr-only"
      :accept="accept"
      :disabled="busy"
      :aria-label="t('Choose a contract file')"
      :aria-describedby="hintId"
      @change="onChange"
    />

    <!-- idle ↔ busy: one grid cell, cross-fade -->
    <span class="grid w-full [&>*]:col-start-1 [&>*]:row-start-1">
      <span
        :class="[
          'grid content-center justify-items-center gap-3 transition-[opacity,visibility] duration-base',
          busy ? 'invisible opacity-0' : 'opacity-100',
        ]"
      >
        <IconTile icon="upload" tone="info" size="lg" />
        <span
          class="inline-flex min-h-[2.75rem] items-center gap-2 rounded-lg bg-sun px-5 py-2 font-semibold text-sun-on transition-colors duration-fast group-hover:bg-sun-hover"
        >
          <AppIcon name="plus" :size="18" />
          {{ t("Choose a file") }}
        </span>
        <span class="text-label text-muted [@media(pointer:coarse)]:hidden">{{ t("or drag it into this box") }}</span>
        <span :id="hintId" class="text-caption text-muted">{{ t("PDF or text file (.txt, .md) · up to 5 MB") }}</span>
      </span>

      <span
        :class="[
          'grid content-center justify-items-center gap-3 transition-[opacity,visibility] duration-base',
          busy ? 'opacity-100' : 'invisible opacity-0',
        ]"
        aria-hidden="true"
      >
        <ThinkingSpinner icon="document" :spinning="busy" />
        <span class="grid gap-1">
          <b class="font-semibold">{{ t("Reading your contract…") }}</b>
          <span v-if="fileName" class="break-all text-label text-muted">{{ fileName }}</span>
        </span>
        <span class="max-w-xs text-label text-muted">
          {{ t("This takes 10–20 seconds. Avida checks every sentence it quotes against your file.") }}
        </span>
      </span>
    </span>

    <!-- drag-over veil (pointer-events off, so it never steals the drag events) -->
    <span
      :class="[
        'pointer-events-none absolute inset-0 grid place-items-center rounded-[0.625rem] bg-mist/95 p-4 font-semibold text-mist-fg transition-opacity duration-fast',
        over ? 'opacity-100' : 'opacity-0',
      ]"
      aria-hidden="true"
    >
      <span class="flex items-center gap-2">
        <AppIcon name="upload" :size="20" />
        {{ t("Drop the file to add it") }}
      </span>
    </span>
  </label>
</template>
