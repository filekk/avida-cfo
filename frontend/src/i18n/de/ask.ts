/**
 * "Ask your CFO", contracts page (upload), Analyst briefing, Legal review of drafts, uploaded-contract pill.
 * English source text → German (formal "Sie").
 */
const de: Record<string, string> = {
  // navigation / page titles
  "Ask your CFO": "Fragen Sie Ihren CFO",
  Contracts: "Verträge",
  "Your contracts": "Ihre Verträge",

  // ask page
  "Ask about your money": "Fragen zu Ihrem Geld",
  "Your agents answer only from your own numbers, contracts and emails – every figure is checked.":
    "Ihre Agenten antworten nur aus Ihren eigenen Zahlen, Verträgen und E-Mails – jede Zahl wird geprüft.",
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

  // overview teaser
  "Questions?": "Fragen?",
  "Your agents answer from your own numbers – instantly for these questions:":
    "Ihre Agenten antworten aus Ihren eigenen Zahlen – bei diesen Fragen sofort:",
  "Ask your own question": "Eigene Frage stellen",

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

  // contracts page
  "The Legal Agent checks every change against these contracts. Add a new one and it is used on the next inbox check.":
    "Der Rechts-Agent prüft jede Änderung gegen diese Verträge. Ein neuer Vertrag wird bei der nächsten Posteingangsprüfung verwendet.",
  "Add a contract": "Vertrag hinzufügen",
  "Upload a contract": "Vertrag hochladen",
  "Drop a file here or click to choose · PDF, .md or .txt · max. 5 MB":
    "Datei hier ablegen oder zum Auswählen klicken · PDF, .md oder .txt · max. 5 MB",
  "The AI model is reading your contract…": "Das KI-Modell liest Ihren Vertrag…",
  "This takes 10–20 seconds. Every quote is checked against the document.":
    "Das dauert 10–20 Sekunden. Jedes Zitat wird mit dem Dokument abgeglichen.",
  "Please choose a PDF, .md or .txt file.": "Bitte wählen Sie eine PDF-, .md- oder .txt-Datei.",
  "The file is larger than 5 MB.": "Die Datei ist größer als 5 MB.",
  "Read: {title}": "Gelesen: {title}",
  "Other party: {party} · {clauses} · {pages} · {seconds} s": "Vertragspartner: {party} · {clauses} · {pages} · {seconds} s",
  "{n} clause": "{n} Klausel",
  "{n} clauses": "{n} Klauseln",
  "{n} page": "{n} Seite",
  "{n} pages": "{n} Seiten",
  "Run the inbox check again – the Legal Agent will use this contract.":
    "Prüfen Sie den Posteingang erneut – der Rechts-Agent verwendet dann diesen Vertrag.",
  "Please double-check:": "Bitte prüfen Sie:",
  "Contracts the Legal Agent knows": "Verträge, die der Rechts-Agent kennt",
  customer: "Kunde",
  supplier: "Lieferant",
  "since {date}": "seit {date}",
  "Prepared in the Jupyter workbench": "Im Jupyter-Workbench vorbereitet",
  "{n} thing to check": "{n} Punkt zu prüfen",
  "{n} things to check": "{n} Punkte zu prüfen",
  Remove: "Entfernen",
  "No contracts yet": "Noch keine Verträge",
  "Upload your first contract above.": "Laden Sie oben Ihren ersten Vertrag hoch.",
};

export default de;
