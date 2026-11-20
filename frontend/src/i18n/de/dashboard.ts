/** Overview: headline, KPIs, waiting decisions, findings teaser (owner: main thread). English → German ("Sie"). */
const de: Record<string, string> = {
  "Key figures": "Kennzahlen",
  "In the bank today": "Heute auf dem Konto",
  "Lowest balance ahead": "Niedrigster Kontostand",
  "below cushion": "unter dem Puffer",
  "above cushion": "über dem Puffer",
  "Your safety cushion": "Ihr Sicherheitspuffer",
  "minimum to keep": "Mindestbetrag",
  Forecast: "Prognose",
  "Your money, next {period}": "Ihr Geld, nächste {period}",
  "Biggest payments ahead": "Größte anstehende Zahlungen",
  "Next {period}": "Nächste {period}",
  "1 decision is waiting for you": "1 Entscheidung wartet auf Sie",
  "{n} decisions are waiting for you": "{n} Entscheidungen warten auf Sie",
  "From your inbox": "Aus Ihrem Posteingang",
  "What I found": "Was ich gefunden habe",

  // headline sentence (components/dashboard/headline.ts – same logic as the backend's)
  "You're safe for the next {n} days. Your balance stays above your safety cushion.":
    "Sie sind die nächsten {n} Tage auf der sicheren Seite. Ihr Kontostand bleibt über Ihrem Sicherheitspuffer.",
  "You're safe for the next {n} days. Around {date} your balance drops to {min} – below your safety cushion of {buffer}.":
    "Sie sind die nächsten {n} Tage auf der sicheren Seite. Um den {date} sinkt Ihr Kontostand auf {min} – unter Ihren Sicherheitspuffer von {buffer}.",
  "You're safe for the next {n} days. From {date} your balance falls below your safety cushion, and on {minDate} your account would be {abs} overdrawn.":
    "Sie sind die nächsten {n} Tage auf der sicheren Seite. Ab dem {date} liegt Ihr Kontostand unter Ihrem Sicherheitspuffer, und am {minDate} wäre Ihr Konto mit {abs} überzogen.",

  // headline banner + ring
  "You're on track": "Alles im Plan",
  "Heads-up": "Achtung",
  "of {n} days": "von {n} Tagen",
  "{days} of {n} days safe": "{days} von {n} Tagen sicher",
};
export default de;
