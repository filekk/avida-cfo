<script setup lang="ts">
import { ref } from "vue";
import ThinkingSpinner from "@/components/sync/ThinkingSpinner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { t } from "@/i18n";

/**
 * Drop zone + file picker for a contract (PDF / .md / .txt). Checks type and size before emitting,
 * so the owner gets an instant message instead of a 422 after the upload.
 * The parent does the upload; `busy` shows the "the model is reading it" state (10–20 s).
 */
const props = defineProps<{ busy?: boolean; accept: string; maxBytes: number }>();
const emit = defineEmits<{ file: [file: File]; invalid: [message: string] }>();

const over = ref(false);

function take(files: FileList | null | undefined) {
  const f = files?.[0];
  if (!f || props.busy) return;
  const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();
  if (!props.accept.split(",").includes(ext)) return emit("invalid", t("Please choose a PDF, .md or .txt file."));
  if (f.size > props.maxBytes) return emit("invalid", t("The file is larger than 5 MB."));
  emit("file", f);
}

function onChange(e: Event) {
  const el = e.target as HTMLInputElement;
  take(el.files);
  el.value = ""; // same file can be picked again
}
</script>

<template>
  <label
    :class="[
      'grid cursor-pointer place-items-center gap-3 rounded-xl border-2 border-dashed p-6 text-center transition-colors duration-base',
      over ? 'border-fg/50 bg-mist' : 'border-line bg-input/50 hover:border-fg/30',
      busy ? 'pointer-events-none' : '',
    ]"
    @dragover.prevent="over = true"
    @dragleave="over = false"
    @drop.prevent="
      over = false;
      take($event.dataTransfer?.files);
    "
  >
    <input type="file" class="sr-only" :accept="accept" :disabled="busy" @change="onChange" />
    <template v-if="busy">
      <ThinkingSpinner icon="document" />
      <span class="grid gap-1" role="status">
        <b>{{ t("The AI model is reading your contract…") }}</b>
        <span class="text-label text-muted">{{ t("This takes 10–20 seconds. Every quote is checked against the document.") }}</span>
      </span>
    </template>
    <template v-else>
      <span class="grid h-12 w-12 place-items-center rounded-xl bg-surface text-fg"><AppIcon name="upload" :size="22" /></span>
      <span class="grid gap-1">
        <b>{{ t("Upload a contract") }}</b>
        <span class="text-label text-muted">{{ t("Drop a file here or click to choose · PDF, .md or .txt · max. 5 MB") }}</span>
      </span>
    </template>
  </label>
</template>
