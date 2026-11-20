/**
 * Contracts page: the Legal Agent's contract list + the upload. English source text → German (formal "Sie").
 */
const de: Record<string, string> = {
  // navigation / page titles
  Contracts: "Verträge",
  "Your contracts": "Ihre Verträge",

  // page header + list
  "When a supplier raises prices or a customer pays late, Avida checks it against these contracts. A contract you add counts from the next inbox check.":
    "Wenn ein Lieferant die Preise erhöht oder ein Kunde zu spät zahlt, prüft Avida das anhand dieser Verträge. Ein neu hinzugefügter Vertrag zählt ab der nächsten Posteingangsprüfung.",
  "Add a contract": "Vertrag hinzufügen",
  "Contracts Avida knows": "Verträge, die Avida kennt",
  "{n} supplier": "{n} Lieferant",
  "{n} suppliers": "{n} Lieferanten",
  "{n} customer": "{n} Kunde",
  "{n} customers": "{n} Kunden",
  "No contracts yet": "Noch keine Verträge",
  "Add your first contract. Avida then checks price changes and late payments against it.":
    "Fügen Sie Ihren ersten Vertrag hinzu. Avida prüft dann Preisänderungen und verspätete Zahlungen anhand dieses Vertrags.",

  // one contract row
  Supplier: "Lieferant",
  Customer: "Kunde",
  "Just added": "Neu hinzugefügt",
  "Since {date}": "Seit {date}",
  "{n} key clause": "{n} wichtige Klausel",
  "{n} key clauses": "{n} wichtige Klauseln",
  "Added during setup": "Bei der Einrichtung hinzugefügt",
  "Added by you": "Von Ihnen hinzugefügt",
  "Added by you · read by AI": "Von Ihnen hinzugefügt · von KI gelesen",
  "Please double-check": "Bitte noch einmal prüfen",
  Remove: "Entfernen",
  "Remove the contract with {party}": "Vertrag mit {party} entfernen",
  "Remove this contract?": "Diesen Vertrag entfernen?",
  "Avida will no longer use it to check your emails. You can add it again at any time.":
    "Avida nutzt ihn dann nicht mehr, um Ihre E-Mails zu prüfen. Sie können ihn jederzeit wieder hinzufügen.",
  "Yes, remove": "Ja, entfernen",
  Cancel: "Abbrechen",
  "Contract removed: {party}": "Vertrag entfernt: {party}",

  // upload box
  "Avida reads it and picks out what matters: prices, notice periods and payment terms.":
    "Avida liest ihn und findet das Wichtige heraus: Preise, Fristen und Zahlungsziele.",
  "Choose a file": "Datei auswählen",
  "Choose a contract file": "Vertragsdatei auswählen",
  "or drag it into this box": "oder ziehen Sie sie in dieses Feld",
  "PDF or text file (.txt, .md) · up to 5 MB": "PDF oder Textdatei (.txt, .md) · bis 5 MB",
  "Drop the file to add it": "Datei loslassen, um sie hinzuzufügen",
  "Reading your contract…": "Ihr Vertrag wird gelesen…",
  "This takes 10–20 seconds. Avida checks every sentence it quotes against your file.":
    "Das dauert 10–20 Sekunden. Avida gleicht jeden zitierten Satz mit Ihrer Datei ab.",
  "Reading your contract. This takes 10–20 seconds.": "Ihr Vertrag wird gelesen. Das dauert 10–20 Sekunden.",
  "Please choose a PDF or a text file (.txt, .md).": "Bitte wählen Sie eine PDF- oder Textdatei (.txt, .md).",
  "This file is larger than 5 MB. Please choose a smaller one.":
    "Diese Datei ist größer als 5 MB. Bitte wählen Sie eine kleinere.",
  "Avida could not read this file.": "Avida konnte diese Datei nicht lesen.",

  // upload result
  "Contract added": "Vertrag hinzugefügt",
  "Contract added: {party}": "Vertrag hinzugefügt: {party}",
  "{n} page": "{n} Seite",
  "{n} pages": "{n} Seiten",
  "read in {n} second": "in {n} Sekunde gelesen",
  "read in {n} seconds": "in {n} Sekunden gelesen",
  "What Avida found": "Was Avida gefunden hat",
  "Monthly fee": "Monatliche Gebühr",
  "Fixed price until": "Festpreis bis",
  "Notice before a price change": "Ankündigungsfrist für Preisänderungen",
  "Max. price rise per year": "Max. Preiserhöhung pro Jahr",
  "Payment terms": "Zahlungsziel",
  "Changes only in writing": "Änderungen nur schriftlich",
  Yes: "Ja",
  No: "Nein",
  "{n} day": "{n} Tag",
  "{n} days": "{n} Tage",
  "Clauses Avida can quote": "Klauseln, die Avida zitieren kann",
  "Avida uses this contract from your next inbox check. Start it with “{button}” at the top.":
    "Avida nutzt diesen Vertrag ab der nächsten Posteingangsprüfung. Starten Sie sie oben mit „{button}“.",
};

export default de;
