<script setup lang="ts">
import { ref } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import SourceTag from "@/components/agent/SourceTag.vue";
import ThinkingSpinner from "@/components/sync/ThinkingSpinner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { agentIcon } from "@/constants/agents";
import { t } from "@/i18n";
import type { AskTurn } from "@/stores/ask";

/**
 * One question + the agent's answer. The answer text comes from the backend in the UI language.
 * in_data = false → the question can't be answered from the company's data: shown as a calm info note.
 *
 * Motion (chat bubbles, only as a response): the question bubble fades in and rises from its corner; the
 * "looking at the numbers" line follows a moment later. When the answer arrives, that line fades out, the slot
 * grows smoothly to the answer's height (the text below moves down, it doesn't jump) and the answer bubble fades in.
 * `settled` = the answer is fully in place (the chat panel then scrolls it into view).
 */
defineProps<{ turn: AskTurn }>();
const emit = defineEmits<{ settled: [] }>();

const slot = ref<HTMLElement | null>(null);
/** slot height while the thinking line leaves; null = nothing to grow from (first render) */
let fromH: number | null = null;

function holdHeight() {
  const el = slot.value;
  if (!el) return;
  fromH = el.offsetHeight;
  el.style.height = `${fromH}px`;
}

function growHeight() {
  const el = slot.value;
  if (!el || fromH === null) return;
  const from = fromH;
  fromH = null;
  el.style.height = "";
  const to = el.offsetHeight;
  let timer = 0;
  const done = () => {
    window.clearTimeout(timer);
    el.removeEventListener("transitionend", onEnd);
    el.style.height = el.style.transition = el.style.overflow = "";
    emit("settled");
  };
  const onEnd = (e: TransitionEvent) => {
    if (e.target === el && e.propertyName === "height") done();
  };
  if (Math.abs(to - from) < 1) return done();
  el.style.overflow = "hidden";
  el.style.height = `${from}px`;
  void el.offsetHeight; // reflow → the browser registers the start height
  el.style.transition = "height var(--dur-slow) var(--ease-out)";
  el.style.height = `${to}px`;
  el.addEventListener("transitionend", onEnd);
  timer = window.setTimeout(done, 700); // safety net: no transitionend if the panel closes meanwhile
}
</script>

<template>
  <li class="grid gap-3">
    <!-- the owner's question -->
    <p class="ask-q ml-auto max-w-[85%] rounded-lg bg-side px-4 py-2.5 leading-relaxed text-white">
      <span class="sr-only">{{ t("You asked:") }} </span>{{ turn.question }}
    </p>

    <!-- reply slot: thinking → answer / error (out-in; the slot animates its height in between).
         The answer is one plain bubble; the agent is named in its first line (small muted icon, no avatar tile).
         No comments inside <Transition>: in dev they count as extra children. -->
    <div ref="slot">
      <Transition
        name="bubble"
        mode="out-in"
        appear
        appear-active-class="bubble-enter-active bubble-later"
        @before-leave="holdHeight"
        @enter="growHeight"
      >
        <div
          v-if="turn.answer"
          key="answer"
          :class="[
            'grid max-w-[92%] origin-top-left gap-2 rounded-lg border px-4 py-3',
            turn.answer.in_data ? 'border-line bg-surface' : 'border-transparent bg-mist text-mist-fg',
          ]"
        >
          <div class="flex flex-wrap items-center gap-2">
            <span class="flex items-center gap-1.5 text-sm font-semibold">
              <AppIcon :name="agentIcon(turn.answer.agent)" :size="16" class="shrink-0 opacity-70" />{{ t(turn.answer.agent) }}
            </span>
            <AutonomyBadge level="analyzed" />
            <SourceTag :source="turn.answer.source" :only-fallback="false" />
          </div>
          <p class="leading-relaxed">{{ turn.answer.answer }}</p>
        </div>

        <p v-else-if="turn.error" key="error" class="flex origin-top-left items-start gap-2 rounded-lg bg-negative-soft p-3 text-negative" role="alert">
          <AppIcon name="alert" :size="18" class="mt-0.5" /> {{ turn.error }}
        </p>

        <div v-else key="thinking" class="flex origin-top-left items-center gap-3 text-muted">
          <ThinkingSpinner size="sm" />
          <span role="status">{{ t("Your agents are looking at the numbers…") }}</span>
        </div>
      </Transition>
    </div>
  </li>
</template>

<style scoped>
/* A bubble arrives: fades in, rises 8px and grows from 98 % out of its own corner (question: bottom right,
   answer: top left). Leaving (the thinking line) is a quick fade. Reduced motion cuts all of it (main.css). */
.ask-q {
  transform-origin: bottom right;
  animation: bubble-in var(--dur-slow) var(--ease-out) both;
}
@keyframes bubble-in {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.98);
  }
}
.bubble-enter-active {
  transition: opacity var(--dur-slow) var(--ease-out), transform var(--dur-slow) var(--ease-out);
}
.bubble-enter-from {
  opacity: 0;
  transform: translateY(8px) scale(0.98);
}
.bubble-leave-active {
  transition: opacity var(--dur-fast) var(--ease-out);
}
.bubble-leave-to {
  opacity: 0;
}
/* first render: the reply line follows the question bubble a moment later */
.bubble-later {
  transition-delay: 120ms;
}
</style>
