/**
 * Action center, decision tiles / focus view, action cards, findings split, finding cards (owner: i18n sweep).
 * English source text → German (formal "Sie"). Backend texts (titles, drafts, contract quotes…) are NOT here.
 */
const de: Record<string, string> = {
  // finding kinds from the current backend (findings/describe.ts): price change · late payment · no figures
  Unknown: "Unbekannt",
  "No figures": "Keine Zahlen",
  "The email announces a change but gives no exact numbers.":
    "Die E-Mail kündigt eine Änderung an, nennt aber keine genauen Zahlen.",
  "{n} days late": "{n} Tage zu spät",
  "Late payment": "Verspätete Zahlung",
  "{supplier}: late payment": "{supplier}: verspätete Zahlung",
  "Invoice {invoice} · due {due} → now {now}": "Rechnung {invoice} · fällig {due} → jetzt {now}",
  "Invoice amount": "Rechnungsbetrag",
  "Days late": "Tage Verzug",
  "Lowest balance drops by": "Tiefster Kontostand sinkt um",
  Invoice: "Rechnung",
  "Remind them to pay on time": "An pünktliche Zahlung erinnern",
  "Ask for the exact figures": "Nach den genauen Zahlen fragen",
  "Cannot be checked – please review": "Nicht prüfbar – bitte ansehen",
  "Price changes and late payments, checked against your contracts.":
    "Preisänderungen und verspätete Zahlungen, geprüft anhand Ihrer Verträge.",

  // Action center page
  "Everything you can act on. Pick an item to see why Avida suggests it – then approve, edit or decline.":
    "Alles, worüber Sie entscheiden können. Wählen Sie einen Eintrag, um zu sehen, warum Avida ihn vorschlägt – dann freigeben, bearbeiten oder ablehnen.",
  Summary: "Zusammenfassung",
  "Waiting for you": "Wartet auf Sie",
  "Already approved": "Bereits freigegeben",
  "Based on your emails": "Aus Ihren E-Mails",
  "Based on your forecast": "Aus Ihrer Prognose",
  "Supplier price changes, checked against your contracts.": "Preisänderungen von Lieferanten, geprüft anhand Ihrer Verträge.",
  "Steps that keep your balance above your safety cushion.": "Schritte, die Ihren Kontostand über dem Sicherheitspuffer halten.",
  "No email needs your decision right now.": "Gerade braucht keine E-Mail Ihre Entscheidung.",
  "Your forecast needs no action right now.": "Für Ihre Prognose ist gerade nichts zu tun.",
  Pending: "Offen",
  Resolved: "Erledigt",
  "Nothing resolved yet.": "Noch nichts erledigt.",
  "Nothing here yet": "Noch nichts da",
  "Use “{button}” at the top. Everything Avida finds and suggests shows up here.":
    "Nutzen Sie oben „{button}“. Alles, was Avida findet und vorschlägt, erscheint hier.",

  // decision states & tile gist
  Approved: "Freigegeben",
  Declined: "Abgelehnt",
  "No action needed": "Nichts zu tun",
  Overdraft: "Kreditlinie",
  "Bridge {from} – {until}": "Überbrückung {from} – {until}",
  "Within your contract": "Im Rahmen Ihres Vertrags",
  Decision: "Entscheidung",
  Amount: "Betrag",
  "Would have saved": "Hätte gespart",
  "You save / year": "Sie sparen / Jahr",
  "Extra / year": "Mehrkosten / Jahr",

  // focus view
  "All actions": "Alle Aktionen",
  "{position} of {total}": "{position} von {total}",
  "Previous decision": "Vorherige Entscheidung",
  "Next decision": "Nächste Entscheidung",
  "{supplier}: price change": "{supplier}: Preisänderung",
  "by {agent}": "von {agent}",

  // action card
  "You save": "Sie sparen",
  "You save (next 12 months)": "Sie sparen (nächste 12 Monate)",
  "Why:": "Warum:",
  To: "An",
  "you can edit it": "Sie können den Text bearbeiten",
  Needed: "Benötigt",
  "Max. interest": "Max. Zinsen",
  "{rate} % a year": "{rate} % pro Jahr",
  "Approve and send": "Freigeben und senden",
  "Approve and apply": "Freigeben und beantragen",
  "Not now": "Jetzt nicht",
  "You declined this. Nothing was done.": "Sie haben abgelehnt. Es wurde nichts ausgeführt.",

  // finding card + split screen
  "from {date}": "ab {date}",
  "{amount} / year": "{amount} / Jahr",
  "What the email says": "Was die E-Mail sagt",
  "The email says": "Die E-Mail sagt",
  "Hide the email": "E-Mail ausblenden",
  "Read the email from {name}": "E-Mail von {name} lesen",
  "What your contract says": "Was Ihr Vertrag sagt",
  "Your contract says": "Ihr Vertrag sagt",
  "No contract on file": "Kein Vertrag hinterlegt",
  "page {n}": "Seite {n}",
  Verdict: "Ergebnis",
  "(passed)": "(erfüllt)",
  "(failed)": "(nicht erfüllt)",
  "Extra per month": "Mehrkosten pro Monat",
  "Within your forecast": "Im Prognosezeitraum",
  "Next 12 months": "Nächste 12 Monate",
  "Show calculation": "Berechnung zeigen",
  "Hide calculation": "Berechnung ausblenden",

  // price bar
  "Monthly price goes from {from} to {to}": "Monatspreis: von {from} auf {to}",
  Before: "Vorher",
  Now: "Jetzt",
  "/month": "/Monat",
  // AV Rewrite (decision bar in the focus view)
  "AV Rewrite": "AV Umschreiben",
  "Rewriting…": "Wird umgeschrieben …",
  "Rewrite the draft with AI": "Entwurf mit KI umschreiben",
  "How should the email change?": "Wie soll sich die E-Mail ändern?",
  "Avida rewrites the draft. Nothing is sent – you read it first.":
    "Avida schreibt den Entwurf um. Es wird nichts gesendet – Sie lesen ihn zuerst.",
  "Quick wishes": "Schnelle Wünsche",
  "Be firmer": "Bestimmter formulieren",
  "Be friendlier": "Freundlicher formulieren",
  "Make it shorter": "Kürzer fassen",
  "Mention a 2 % discount for paying early": "2 % Skonto bei früher Zahlung erwähnen",
  "Your wish for the email": "Ihr Wunsch für die E-Mail",
  "e.g. be firmer, mention the discount": "z. B. bestimmter, Rabatt erwähnen",
  Rewrite: "Umschreiben",
  "Rewritten by Avida – please read it before sending.": "Von Avida umgeschrieben – bitte vor dem Senden lesen.",
  Undo: "Rückgängig",
  "Version {n}": "Version {n}",
  "The draft is unchanged.": "Der Entwurf ist unverändert.",
  "New version checked by the Legal Agent – approved": "Neue Version vom Rechts-Agenten geprüft – freigegeben",
  "Your text passes the checks": "Ihr Text besteht die Prüfung",
  "Please check before sending:": "Bitte vor dem Senden prüfen:",
  "Approving runs in a safe test mode – nothing really leaves your company.":
    "Die Freigabe läuft in einem sicheren Testmodus – nichts verlässt wirklich Ihr Unternehmen.",
};
export default de;
