/**
 * Policy, history, not-found pages, autonomy legend/badges, generic UI components (owner: i18n sweep).
 * English source text → German (formal "Sie").
 */
const de: Record<string, string> = {
  // source tag
  "The AI model was unavailable – this is a prepared answer.":
    "Das KI-Modell war nicht erreichbar – dies ist eine vorbereitete Antwort.",

  // policy
  "Reading and calculating: on their own. Anything that leaves your company: only after your click.":
    "Lesen und Rechnen: selbstständig. Alles, was Ihr Unternehmen verlässt: nur nach Ihrem Klick.",
  "The four levels": "Die vier Stufen",
  "Who may do what": "Wer darf was",
  Action: "Aktion",

  // history
  "What happened": "Was passiert ist",
  "Every check and decision, newest first.": "Jede Prüfung und Entscheidung, die neueste zuerst.",
  "Check started": "Prüfung gestartet",
  "Check finished": "Prüfung beendet",
  Approved: "Freigegeben",
  Declined: "Abgelehnt",
  "{n} finding": "{n} Befund",
  "{n} findings": "{n} Befunde",
  "{n} proposed action": "{n} vorgeschlagene Aktion",
  "{n} proposed actions": "{n} vorgeschlagene Aktionen",
  "Nothing has happened yet": "Noch ist nichts passiert",
  "Use “{button}” at the top of the page.": "Nutzen Sie oben auf der Seite „{button}“.",

  // not found
  "This page doesn't exist": "Diese Seite gibt es nicht",
  "The link may be outdated.": "Der Link ist vielleicht veraltet.",
  "Back to overview": "Zurück zur Übersicht",
};
export default de;
