/** Check-my-inbox box + progress pop-up, pipeline, agent steps (owner: sync). English source text → German (formal "Sie"). */
const de: Record<string, string> = {
  // box
  "Check my inbox": "Posteingang prüfen",
  "The check finished, but its result could not be read. Please reload the page.":
    "Die Prüfung ist fertig, aber ihr Ergebnis konnte nicht gelesen werden. Bitte laden Sie die Seite neu.",
  "Checking your inbox": "Ihr Posteingang wird geprüft",
  "Inbox checked": "Posteingang geprüft",
  // second line under "Inbox checked" ("5 minutes ago" itself comes from Intl.RelativeTimeFormat)
  "just now": "gerade eben",
  "last checked {when}": "zuletzt geprüft {when}",
  "Check failed": "Prüfung fehlgeschlagen",
  "{n} to approve": "{n} zur Freigabe",
  "Inbox check": "Posteingangsprüfung",

  // what the agent at work is doing right now (constants/agents.ts)
  "Starting…": "Wird gestartet…",
  "Reading your emails…": "Ihre E-Mails werden gelesen…",
  "Checking your contracts…": "Ihre Verträge werden geprüft…",
  "Updating your forecast…": "Ihre Prognose wird aktualisiert…",
  "Reading emails and forecasting…": "E-Mails werden gelesen, Prognose wird erstellt…",
  "Drafting your replies…": "Ihre Antworten werden entworfen…",
  "Reads emails, forecasts cash": "Liest E-Mails, plant die Liquidität",
  "Drafts your replies": "Entwirft Ihre Antworten",
  "Crunching the numbers…": "Die Zahlen werden berechnet…",
  "Writing the replies…": "Die Antworten werden geschrieben…",
  "Working…": "Wird bearbeitet…",

  // one-word agent names in the pipeline
  Inbox: "Posteingang",
  Contract: "Vertrag",
  Liquidity: "Liquidität",
  Analyst: "Analyse",
  Legal: "Recht",
  Negotiator: "Verhandlung",
  Agent: "Agent",
  "not started": "nicht begonnen",
  "in progress": "läuft",
  done: "erledigt",

  // pop-up
  "Let Avida check your inbox": "Lassen Sie Avida Ihren Posteingang prüfen",
  "Avida reads your new emails, checks them against your contracts and updates your forecast.":
    "Avida liest Ihre neuen E-Mails, prüft sie anhand Ihrer Verträge und aktualisiert Ihre Prognose.",
  "Step {n}": "Schritt {n}",
  "{n} step, all done": "{n} Schritt, alles erledigt",
  "{n} steps, all done": "{n} Schritte, alles erledigt",
  "Your last check is done.": "Ihre letzte Prüfung ist abgeschlossen.",
  "Run a new check to see every step again.": "Starten Sie eine neue Prüfung, um wieder jeden Schritt zu sehen.",
  Hide: "Ausblenden",
  "What your assistant did": "Was Ihr Assistent getan hat",
  to: "an",
  "thing found": "Auffälligkeit gefunden",
  "things found": "Auffälligkeiten gefunden",
  "waits for you": "wartet auf Sie",
  "wait for you": "warten auf Sie",
  "Review decisions": "Entscheidungen ansehen",
  "Open Action center": "Aktionszentrale öffnen",
  "Check again": "Erneut prüfen",
  "Start over": "Neu beginnen",
  Dismiss: "Hinweis schließen",
  "Nothing is sent without your OK.": "Ohne Ihr OK wird nichts gesendet.",
};
export default de;
