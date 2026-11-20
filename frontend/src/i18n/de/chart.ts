/** Forecast chart, period picker, payments donut (owner: chart). English source text → German (formal "Sie"). */
const de: Record<string, string> = {
  // period (titles "Your money, next {period}", picker)
  "{n} day": "{n} Tag",
  "{n} days": "{n} Tage",
  "12 months": "12 Monate",
  "Forecast period": "Prognosezeitraum",
  Week: "Woche",
  Month: "Monat",
  "3 months": "3 Monate",
  Year: "Jahr",
  Custom: "Individuell",
  days: "Tage",
  "Number of days to show (up to {max})": "Anzahl der angezeigten Tage (bis {max})",
  "Avida forecasts {max} days for now.": "Avida erstellt derzeit eine Prognose für {max} Tage.",

  // chart lines (scenario names) – long for the read-out, short for the hover bubble
  "If you follow Avida's advice": "Wenn Sie Avidas Rat folgen",
  "If you accept every price increase": "Wenn Sie jede Preiserhöhung akzeptieren",
  "Your forecast": "Ihre Prognose",
  "Follow Avida's advice": "Avidas Rat folgen",
  "Accept all increases": "Alle Erhöhungen akzeptieren",

  // chart
  "Forecast chart. Click a day or use the arrow keys. Hold Shift to select a period. Escape goes back to today.":
    "Prognosediagramm. Klicken Sie auf einen Tag oder nutzen Sie die Pfeiltasten. Halten Sie die Umschalttaste gedrückt, um einen Zeitraum zu wählen. Escape führt zurück zu heute.",
  "Cash forecast for the next {n} days. Lowest balance {amount} on {date}.":
    "Liquiditätsprognose für die nächsten {n} Tage. Tiefster Kontostand {amount} am {date}.",
  "Safety cushion {amount}": "Sicherheitspuffer {amount}",
  "Cushion {amount}": "Puffer {amount}",
  "Lowest · {date}": "Tiefster Stand · {date}",
  "Click a day to see it · drag to compare a period": "Klicken Sie auf einen Tag · ziehen Sie, um einen Zeitraum zu vergleichen",
  "Tap a day to see it · swipe sideways to compare a period":
    "Tippen Sie auf einen Tag · wischen Sie seitwärts, um einen Zeitraum zu vergleichen",

  // read-out
  "in {n} day": "in {n} Tag",
  "in {n} days": "in {n} Tagen",
  "from today": "ab heute",
  "starts in {n} day": "beginnt in {n} Tag",
  "starts in {n} days": "beginnt in {n} Tagen",
  "vs today": "gegenüber heute",
  "below cushion": "unter dem Puffer",
  "Lowest ahead {amount} · {date}": "Tiefster Stand {amount} · {date}",
  "lowest {amount} on {date}": "tiefster Stand {amount} am {date}",
  "{n} day below cushion": "{n} Tag unter dem Puffer",
  "{n} days below cushion": "{n} Tage unter dem Puffer",
  "always above cushion": "immer über dem Puffer",
  "Big payments in this range": "Große Zahlungen in diesem Zeitraum",
  "No big payments in this range": "Keine großen Zahlungen in diesem Zeitraum",
  "Big payments": "Große Zahlungen",
  Lowest: "Tiefster Stand",
  "Jump to the lowest point": "Zum tiefsten Stand springen",
  "Back to today": "Zurück zu heute",

  // payments donut
  Total: "Gesamt",
  Payments: "Zahlungen",
  "{n} payment": "{n} Zahlung",
  "{n} payments": "{n} Zahlungen",
  "in {n} payment": "in {n} Zahlung",
  "in {n} payments": "in {n} Zahlungen",
  "No big payments in this period": "Keine großen Zahlungen in diesem Zeitraum",
  "Avida looks at your biggest single payments. None of them falls in this period.":
    "Avida betrachtet Ihre größten Einzelzahlungen. Keine davon fällt in diesen Zeitraum.",
  "Your biggest single payments only (top 5 of the forecast). Smaller costs are left out.":
    "Nur Ihre größten Einzelzahlungen (Top 5 der Prognose). Kleinere Kosten sind nicht enthalten.",
  "Biggest payments in the next {period}: {list}. Total {total}.":
    "Größte Zahlungen der nächsten {period}: {list}. Gesamt {total}.",
};
export default de;
