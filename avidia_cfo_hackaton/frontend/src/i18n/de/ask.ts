/**
 * "Ask your CFO", Analyst briefing, Legal review of drafts, uploaded-contract pill.
 * (The contracts page lives in de/contracts.ts.) English source text → German (formal "Sie").
 */
const de: Record<string, string> = {
  // Action center card + floating chat on the overview
  "Ask your CFO": "Fragen Sie Ihren CFO",
  "Not sure about a decision? Ask in your own words.":
    "Unsicher bei einer Entscheidung? Fragen Sie einfach in Ihren eigenen Worten.",
  "Answers only from your own numbers": "Antworten nur aus Ihren eigenen Zahlen",
  "new answer": "neue Antwort",

  // the chat (components/ask)
  "What would you like to know?": "Was möchten Sie wissen?",
  "Pick a question below or type your own.": "Wählen Sie unten eine Frage oder schreiben Sie Ihre eigene.",
  Conversation: "Unterhaltung",
  "Suggested questions": "Vorgeschlagene Fragen",
  "Your question": "Ihre Frage",
  "e.g. Can I pay my employees in January?": "z. B. Kann ich im Januar meine Löhne zahlen?",
  Ask: "Fragen",
  "Typed questions take a few seconds – the AI model writes the answer.":
    "Eigene Fragen dauern ein paar Sekunden – das KI-Modell schreibt die Antwort.",
  "Start a new conversation": "Neue Unterhaltung beginnen",
  "You asked:": "Ihre Frage:",
  "Your agents are looking at the numbers…": "Ihre Agenten sehen sich die Zahlen an…",

  // Analyst briefing
  "Analyst briefing": "Lagebericht des Analysten",
  "Low risk": "Geringes Risiko",
  "Medium risk": "Mittleres Risiko",
  "High risk": "Hohes Risiko",

  // Legal review of the draft
  "Checked by {agent} – approved": "Geprüft: {agent} – freigegeben",
  "Checked by {agent} – approved after one revision": "Geprüft: {agent} – nach einer Überarbeitung freigegeben",
  "Checked by {agent} – please read it before sending": "Geprüft: {agent} – bitte vor dem Senden lesen",

  // uploaded contract in a finding
  "Uploaded by you · terms read by the AI model": "Von Ihnen hochgeladen · Bedingungen vom KI-Modell gelesen",
  "Uploaded by you · cached answer": "Von Ihnen hochgeladen · gespeicherte Antwort",
  // contextual "Ask your CFO" inside one decision (components/ask/AskContext + contextual.ts)
  "Questions about this case? Pick one below or ask in your own words.":
    "Fragen zu diesem Fall? Wählen Sie unten eine aus oder fragen Sie in eigenen Worten.",
  Open: "Öffnen",
  "Quick questions": "Schnelle Fragen",
  "Your question about this case": "Ihre Frage zu diesem Fall",
  "Ask about this case…": "Fragen Sie zu diesem Fall …",
  "How does the late payment from {party} affect my balance?": "Wie wirkt sich die verspätete Zahlung von {party} auf meinen Kontostand aus?",
  "Can I charge {party} interest for paying late?": "Kann ich {party} Verzugszinsen berechnen?",
  "What does it cost me if I just pay the new {party} price?": "Was kostet es mich, wenn ich den neuen Preis von {party} einfach zahle?",
  "What happens if {party} refuses my reply?": "Was passiert, wenn {party} meine Antwort ablehnt?",
  "Why is the {party} increase allowed?": "Warum ist die Erhöhung von {party} erlaubt?",
  "Can I still ask {party} for a better price?": "Kann ich {party} trotzdem um einen besseren Preis bitten?",
  "What should I check in the {party} email?": "Was sollte ich in der E-Mail von {party} prüfen?",
  "How much does the overdraft cost me in total?": "Was kostet mich die Kreditlinie insgesamt?",
  "What happens if I don't take the overdraft?": "Was passiert, wenn ich die Kreditlinie nicht nehme?",
  "How does this decision change my cash forecast?": "Wie verändert diese Entscheidung meine Liquiditätsprognose?",
};

export default de;
