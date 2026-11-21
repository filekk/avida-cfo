<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import { onBeforeRouteLeave } from "vue-router";
import AppIcon from "@/components/ui/AppIcon.vue";
import { t } from "@/i18n";
import { useAskStore } from "@/stores/ask";
import { prefersReducedMotion } from "@/utils/motion";
import AskChat from "./AskChat.vue";

/** Module level: the bubble introduces itself only the first time the overview is shown after loading the app. */
let introduced = false;

/**
 * Floating "Ask your CFO" bubble (Overview only), like the chat assistants on typical websites.
 *   - sun-yellow circle bottom-right with a navy icon (owner's choice: easy to find); click opens / closes the panel.
 *     On the first visit after loading the app it pops in once with one soft ring – then it never moves on its own
 *   - ≥ 640px: non-modal panel above the bubble (24rem, ≤ 70vh) – the page stays fully usable
 *   - phones: bottom sheet over the page with a scrim and its own close button (modal: Tab stays inside)
 *   - Escape or the close button closes and focus returns to the bubble. Opening focuses the question field
 *     (touch phones focus the dialog instead, so the keyboard doesn't cover the suggested questions)
 *   - never covers the footer: while the footer scrolls into view, bubble and panel ride up with it
 *     (IntersectionObserver switches a rAF-throttled scroll listener on only while the footer is visible)
 *   - the root is an in-flow spacer, so at the very bottom the bubble covers no content of the page either
 *   - bubble + panel are teleported to <body>: the route transition's transform would break position: fixed
 * The conversation is the shared ask store, so it is the same one as in the Action center.
 */
const store = useAskStore();

const open = ref(false);
/** Mount the chat on the first open, then keep it (draft and scroll position survive closing). */
const everOpened = ref(false);
/** Fades out together with the page on navigation (the teleported part doesn't get the page transition). */
const leaving = ref(false);
const bubble = ref<HTMLButtonElement | null>(null);
const panel = ref<HTMLElement | null>(null);
const chat = ref<InstanceType<typeof AskChat> | null>(null);

const uid = useId();
const panelId = `ask-panel-${uid}`;
const titleId = `ask-title-${uid}`;

const phoneQuery = window.matchMedia("(max-width: 639.98px)");
const finePointer = window.matchMedia("(pointer: fine)");
const phone = ref(phoneQuery.matches);
const onPhoneChange = () => (phone.value = phoneQuery.matches);

// --- open / close ------------------------------------------------------------------------------------
async function show(viaKeyboard: boolean) {
  open.value = true;
  everOpened.value = true;
  unseen.value = false;
  await nextTick();
  chat.value?.scrollToLatest("auto");
  if (viaKeyboard || finePointer.matches) chat.value?.focus();
  else panel.value?.focus();
}
function close() {
  open.value = false;
  bubble.value?.focus();
}
/** Enter / Space fire a click with detail 0 → keyboard users always land in the question field. */
const toggle = (e: MouseEvent) => (open.value ? close() : show(e.detail === 0));

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
function onPanelKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    e.stopPropagation();
    close();
    return;
  }
  // phones = modal sheet: keep Tab inside it (desktop is non-modal – Tab may leave)
  if (e.key !== "Tab" || !phone.value || !panel.value) return;
  const els = [...panel.value.querySelectorAll<HTMLElement>(FOCUSABLE)].filter((el) => el.offsetParent !== null);
  const first = els[0];
  const last = els[els.length - 1];
  if (!first || !last) return;
  const active = document.activeElement;
  if (e.shiftKey && (active === first || active === panel.value)) {
    e.preventDefault();
    last.focus();
  } else if (!e.shiftKey && active === last) {
    e.preventDefault();
    first.focus();
  }
}

// --- an answer arrived while the panel was closed → small dot on the bubble ---------------------------
const unseen = ref(false);
watch(
  () => store.generalTurns.filter((x) => x.answer || x.error).length, // the overview chat only
  (n, was) => {
    if (n > was && !open.value) unseen.value = true;
  },
);
const bubbleLabel = computed(() => (unseen.value ? `${t("Ask your CFO")}, ${t("new answer")}` : t("Ask your CFO")));

// --- first appearance: a short "here I am" (once per app load, never with reduced motion) ----------------
const introduce = ref(false);
function onIntroEnd(e: AnimationEvent) {
  if ((e.target as HTMLElement).classList.contains("ask-ring")) introduce.value = false;
}

// --- stay above the footer ----------------------------------------------------------------------------
const lift = ref(0);
let footer: Element | null = null;
let io: IntersectionObserver | null = null;
let ro: ResizeObserver | null = null;
let raf = 0;
let following = false;

function measure() {
  raf = 0;
  if (footer) lift.value = Math.max(0, Math.round(window.innerHeight - footer.getBoundingClientRect().top));
}
function schedule() {
  if (!raf) raf = requestAnimationFrame(measure);
}
function follow(on: boolean) {
  if (on === following) return;
  following = on;
  if (on) {
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
  } else {
    window.removeEventListener("scroll", schedule);
    window.removeEventListener("resize", schedule);
  }
}

onMounted(() => {
  if (!introduced && !prefersReducedMotion()) introduce.value = true;
  introduced = true;
  phoneQuery.addEventListener("change", onPhoneChange);
  // the app footer (AppLayout: <main id="main"> + <footer>), not a <footer> inside some card
  footer = document.querySelector("#main ~ footer");
  if (footer) {
    io = new IntersectionObserver(
      ([entry]) => {
        follow(!!entry?.isIntersecting);
        measure();
      },
      { threshold: [0, 0.5, 1] },
    );
    io.observe(footer);
    // page height changes without scrolling (data loads, chart period) move the footer too
    ro = new ResizeObserver(schedule);
    ro.observe(document.body);
  }
  // fetch the chips early → instant suggestions when the panel opens
  if (!store.suggestions.length && !store.loadingSuggestions) store.loadSuggestions();
});
onBeforeUnmount(() => {
  phoneQuery.removeEventListener("change", onPhoneChange);
  io?.disconnect();
  ro?.disconnect();
  follow(false);
  cancelAnimationFrame(raf);
});
onBeforeRouteLeave(() => {
  leaving.value = true;
});
</script>

<template>
  <div class="h-10" aria-hidden="true">
    <!-- in-flow spacer (bubble clearance at the bottom of the page); the launcher itself lives in <body> -->
    <Teleport to="body">
      <div
        :class="['ask-launcher transition-opacity duration-fast', leaving ? 'pointer-events-none opacity-0' : '']"
        :style="{ '--ask-lift': `${lift}px` }"
      >
        <!-- phones: scrim behind the sheet (tap = close) -->
        <Transition name="fade">
          <div v-if="open && phone" class="fixed inset-0 z-40 bg-side/50" aria-hidden="true" @click="close" />
        </Transition>

        <Transition
          enter-active-class="transition duration-base ease-out"
          leave-active-class="transition duration-fast ease-out"
          enter-from-class="translate-y-full opacity-0 sm:translate-y-2 sm:scale-95"
          leave-to-class="translate-y-full opacity-0 sm:translate-y-2 sm:scale-95"
        >
          <section
            v-show="open"
            :id="panelId"
            ref="panel"
            role="dialog"
            :aria-labelledby="titleId"
            :aria-modal="phone ? 'true' : undefined"
            tabindex="-1"
            class="ask-panel flex flex-col overflow-hidden border border-line bg-surface text-fg shadow-pop focus:outline-none"
            @keydown="onPanelKeydown"
          >
            <header class="flex shrink-0 items-center gap-3 border-b border-line py-2.5 pl-4 pr-2">
              <div class="min-w-0 flex-1">
                <h2 :id="titleId" class="text-base font-semibold leading-tight">{{ t("Ask your CFO") }}</h2>
                <p class="text-caption text-muted">{{ t("Answers only from your own numbers") }}</p>
              </div>
              <button
                type="button"
                class="grid h-11 w-11 shrink-0 place-items-center rounded-lg text-muted hover:bg-input hover:text-fg"
                :aria-label="t('Close')"
                :title="t('Close')"
                @click="close"
              >
                <AppIcon name="x" :size="22" />
              </button>
            </header>
            <AskChat v-if="everOpened" ref="chat" compact />
          </section>
        </Transition>

        <!-- the bubble: the dock rides up above the footer (--ask-lift). Sun yellow with a navy icon.
             First visit in this app session: it pops in once and sends one soft ring out ("here I am"), then rests. -->
        <div :class="['ask-dock', introduce ? 'is-intro' : '']" @animationend="onIntroEnd">
            <span class="ask-ring pointer-events-none absolute inset-0 rounded-full border-2 border-sun opacity-0" aria-hidden="true" />
            <button
              ref="bubble"
              type="button"
              :class="[
                'ask-bubble relative grid h-14 w-14 place-items-center rounded-full bg-sun text-sun-on shadow-pop ring-1 ring-sun-on/10',
                'transition-[transform,background-color] duration-fast hover:bg-sun-hover active:scale-[0.98]',
                open ? 'is-open' : '',
              ]"
              :aria-label="bubbleLabel"
              :aria-expanded="open"
              :aria-controls="panelId"
              @click="toggle"
              @keydown.esc="open && close()"
            >
              <!-- icon: chat ↔ chevron, both in one cell, cross-fade + turn.
                   The chat glyph's tail points bottom-left, so its weight sits there: nudge it up-right to look centred. -->
              <span class="grid translate-x-px -translate-y-px [&>*]:col-start-1 [&>*]:row-start-1" aria-hidden="true">
                <AppIcon
                  name="ask"
                  :size="26"
                  :class="['transition duration-base', open ? 'rotate-90 scale-50 opacity-0' : 'opacity-100']"
                />
                <AppIcon
                  name="chevronDown"
                  :size="26"
                  :class="['transition duration-base', open ? 'opacity-100' : '-rotate-90 scale-50 opacity-0']"
                />
              </span>
              <!-- new answer while closed -->
              <span
                :class="[
                  'absolute right-0.5 top-0.5 h-3.5 w-3.5 rounded-full bg-side ring-2 ring-sun transition duration-base',
                  unseen ? 'scale-100 opacity-100' : 'scale-0 opacity-0',
                ]"
                aria-hidden="true"
              />
              <!-- hover / keyboard-focus label (the accessible name is aria-label) -->
              <span
                class="ask-tip pointer-events-none absolute right-full top-1/2 mr-3 -translate-y-1/2 whitespace-nowrap rounded-lg bg-side px-3 py-1.5 text-label font-semibold text-white opacity-0 shadow-pop transition-opacity duration-fast"
                aria-hidden="true"
              >
                {{ t("Ask your CFO") }}
              </span>
            </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/*
 * Geometry. --ask-lift (px) = how far the footer reaches into the viewport → the dock and the desktop panel
 * move up by exactly that much (no transition on purpose: it follows the scroll like a sticky element).
 */
.ask-launcher {
  --ask-gap: 1rem;
  --ask-bubble: 3.5rem;
}
.ask-dock {
  position: fixed;
  right: var(--ask-gap);
  bottom: calc(var(--ask-gap) + env(safe-area-inset-bottom, 0px));
  z-index: 10; /* above the content, below the sticky top bar and its pop-ups (z-20) */
  transform: translate3d(0, calc(var(--ask-lift, 0px) * -1), 0);
}

/* phones: bottom sheet, almost full height, above the top bar */
.ask-panel {
  position: fixed;
  inset: auto 0 0 0;
  z-index: 50;
  height: calc(100dvh - 2.5rem);
  padding-bottom: env(safe-area-inset-bottom, 0px);
  border-bottom-width: 0;
  border-radius: 0.75rem 0.75rem 0 0;
}

@media (min-width: 640px) {
  .ask-launcher {
    --ask-gap: 1.5rem;
  }
  /* non-modal panel above the bubble; never taller than the room below the top bar */
  .ask-panel {
    --ask-panel-bottom: calc(var(--ask-gap) + env(safe-area-inset-bottom, 0px) + var(--ask-bubble) + 0.75rem + var(--ask-lift, 0px));
    left: auto;
    right: var(--ask-gap);
    bottom: var(--ask-panel-bottom);
    z-index: 10;
    width: min(24rem, calc(100vw - 2 * var(--ask-gap)));
    height: min(70vh, 40rem, calc(100dvh - var(--ask-panel-bottom) - 8.5rem));
    padding-bottom: 0;
    border-bottom-width: 1px;
    border-radius: 0.75rem;
    transform-origin: bottom right;
  }
}
@media (min-width: 1024px) {
  .ask-panel {
    height: min(70vh, 40rem, calc(100dvh - var(--ask-panel-bottom) - 5.5rem));
  }
}

/* first appearance: pop in, then ONE soft ring goes out and fades (≈ 1.9 s in total, then it rests for good) */
.ask-dock.is-intro .ask-bubble {
  animation: ask-pop 520ms var(--ease-out) 350ms both;
}
.ask-dock.is-intro .ask-ring {
  animation: ask-ring 1100ms var(--ease-out) 800ms both;
}
@keyframes ask-pop {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.6);
  }
  60% {
    opacity: 1;
    transform: scale(1.05);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes ask-ring {
  from {
    opacity: 0.8;
    transform: scale(1);
  }
  to {
    opacity: 0;
    transform: scale(1.55);
  }
}

/* tooltip: mouse hover (real hover devices only) or keyboard focus, never while the panel is open */
@media (hover: hover) {
  .ask-bubble:hover:not(.is-open) .ask-tip {
    opacity: 1;
  }
}
.ask-bubble:focus-visible:not(.is-open) .ask-tip {
  opacity: 1;
}
</style>
