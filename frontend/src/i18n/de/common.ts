/** Shared labels used in many places (constants/*, router titles, generic buttons). Formal "Sie" everywhere. */
const de: Record<string, string> = {
  // autonomy levels (challenge requirement – same wording everywhere)
  "Analysed by agent": "Vom Agenten analysiert",
  Recommendation: "Empfehlung",
  "Needs your approval": "Braucht Ihre Freigabe",
  "Simulated execution": "Simulierte Ausführung",
  "Reads and calculates on its own.": "Liest und rechnet selbstständig.",
  "Suggests a step. You decide.": "Schlägt einen Schritt vor. Sie entscheiden.",
  "Waits for your click.": "Wartet auf Ihren Klick.",
  "Runs in a safe sandbox. Nothing leaves.": "Läuft in einer sicheren Testumgebung. Nichts verlässt das System.",

  // answer sources
  "AI model": "KI-Modell",
  "cached answer": "gespeicherte Antwort",
  "rule-based": "regelbasiert",

  // verdicts & recommendations
  "Not allowed by your contract": "Laut Vertrag nicht erlaubt",
  "Allowed by your contract": "Laut Vertrag erlaubt",
  "No contract found – please check": "Kein Vertrag gefunden – bitte prüfen",
  "Reject the increase": "Erhöhung ablehnen",
  "Accept – it's within the contract": "Annehmen – im Rahmen des Vertrags",
  "Check it yourself": "Bitte selbst prüfen",

  // agents (names come from the backend; shown translated) – current and upcoming (backend-dev) names
  "Inbox Agent": "Posteingangs-Agent",
  "Contract Agent": "Vertrags-Agent",
  "Liquidity Agent": "Liquiditäts-Agent",
  "Analyst Agent": "Analyse-Agent",
  "Legal Agent": "Rechts-Agent",
  "Negotiator Agent": "Verhandlungs-Agent",
  "Reads your emails": "Liest Ihre E-Mails",
  "Checks your contracts": "Prüft Ihre Verträge",
  "Updates your forecast": "Aktualisiert Ihre Prognose",
  "Crunches the numbers": "Rechnet die Zahlen durch",
  "Writes the replies": "Schreibt die Antworten",
  You: "Sie",

  // navigation & page titles
  Overview: "Übersicht",
  "Action center": "Aktionszentrale",
  "Agent permissions": "Agenten-Rechte",
  History: "Verlauf",
  "Your money at a glance": "Ihr Geld auf einen Blick",
  "What your agents may do": "Was Ihre Agenten dürfen",
  "Page not found": "Seite nicht gefunden",
  "Main navigation": "Hauptnavigation",

  // money words used in several places
  "Saved by Avida": "Von Avida gespart",
  "next 12 months": "nächste 12 Monate",
  "Saved by Avida (12 months)": "Von Avida gespart (12 Monate)",

  // language switch (top bar)
  Language: "Sprache",
  "Language: {lang}": "Sprache: {lang}",

  // generic buttons & states
  Close: "Schließen",
  "Try again": "Erneut versuchen",
  Refresh: "Aktualisieren",
  "Go to overview": "Zur Übersicht",
  Copy: "Kopieren",
  Copied: "Kopiert",
  "Copied to clipboard": "In die Zwischenablage kopiert",
  Today: "Heute",
  "Something went wrong.": "Etwas ist schiefgelaufen.",
  "Cannot reach the server. Check your connection.": "Der Server ist nicht erreichbar. Bitte prüfen Sie Ihre Verbindung.",
  "Request failed ({status})": "Anfrage fehlgeschlagen ({status})",
  "Connection to the assistant was lost.": "Die Verbindung zum Assistenten wurde unterbrochen.",
};
export default de;
