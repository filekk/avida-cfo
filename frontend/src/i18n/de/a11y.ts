/** Accessibility menu, theme toggle (owner: a11y). English source text → German (formal "Sie"). */
const de: Record<string, string> = {
  // trigger + panel
  "Accessibility settings": "Barrierefreiheit",
  "Close accessibility settings": "Barrierefreiheit schließen",
  "Make Avida easier to use": "Avida einfacher bedienen",
  "Saved on this device.": "Auf diesem Gerät gespeichert.",

  // text size
  "Text size": "Textgröße",
  "Normal text": "Normale Schrift",
  "Large text": "Große Schrift",
  "Larger text": "Größere Schrift",
  "Largest text": "Größte Schrift",

  // contrast
  Contrast: "Kontrast",
  Standard: "Standard",
  "Yellow on black": "Gelb auf Schwarz",

  // colours (theme)
  Colours: "Farben",
  Light: "Hell",
  Dark: "Dunkel",
  Auto: "Auto", // short on purpose: 3 options share ~100px at 390px width (German UIs use "Auto" too)
  "Yellow on black is used while high contrast is on.": "Solange der hohe Kontrast aktiv ist, gilt Gelb auf Schwarz.",

  // switches
  "Reduce motion": "Weniger Bewegung",
  "Fewer animations": "Weniger Animationen",
  "Underline links": "Links unterstreichen",
  "Easier to spot": "Leichter zu erkennen",
  "Easier reading": "Leichter lesen",
  "More space between letters and lines": "Mehr Abstand zwischen Buchstaben und Zeilen",
  "Reset to default": "Auf Standard zurücksetzen",

  // theme toggle (top bar)
  "Switch to light mode": "Zum hellen Modus wechseln",
  "Switch to dark mode": "Zum dunklen Modus wechseln",
  "Light mode": "Heller Modus",
  "Dark mode": "Dunkler Modus",
};
export default de;
