// Shared formatting helpers used across components.

export function formatCurrency(value) {
  const number = Number(value);
  if (Number.isNaN(number)) return '—';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(number);
}

const DATE_LOCALES = { en: 'en-US', es: 'es-ES' };

// `language` is the active UI language ('en' | 'es'), used to pick the
// matching Intl locale so dates render in the user's language.
export function formatDate(value, language = 'en') {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const locale = DATE_LOCALES[language] || DATE_LOCALES.en;
  return date.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' });
}

// Normalizes a display name so every word starts with an uppercase letter and
// the rest is lowercase (e.g. "  juan  CARLOS " -> "Juan Carlos"). Applied when
// creating participants and events so stored names read consistently everywhere.
export function toTitleCase(value) {
  return value
    .trim()
    .replace(/\s+/g, ' ')
    .split(' ')
    .map((word) => (word ? word[0].toUpperCase() + word.slice(1).toLowerCase() : word))
    .join(' ');
}
