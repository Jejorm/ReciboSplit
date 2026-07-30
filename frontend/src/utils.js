// Shared formatting helpers used across components.

export function formatCurrency(value, currency = 'USD') {
  const number = Number(value);
  if (Number.isNaN(number)) return '—';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(number);
}

// Returns just the currency's symbol (e.g. "€", "$"), used where a bare glyph
// is shown next to a plain number input instead of a fully formatted amount.
export function getCurrencySymbol(currency = 'USD') {
  const parts = new Intl.NumberFormat('en-US', { style: 'currency', currency }).formatToParts(0);
  const currencyPart = parts.find((part) => part.type === 'currency');
  return currencyPart ? currencyPart.value : currency;
}

// Curated convenience list for the currency picker. Not exhaustive — the
// picker must still accept typing/selecting any other 3-letter ISO 4217 code,
// since vision-detected currencies aren't limited to this list.
export const CURRENCY_OPTIONS = [
  { code: 'USD', label: 'USD — US Dollar' },
  { code: 'EUR', label: 'EUR — Euro' },
  { code: 'GBP', label: 'GBP — British Pound' },
  { code: 'MXN', label: 'MXN — Mexican Peso' },
  { code: 'COP', label: 'COP — Colombian Peso' },
  { code: 'ARS', label: 'ARS — Argentine Peso' },
  { code: 'CLP', label: 'CLP — Chilean Peso' },
  { code: 'BRL', label: 'BRL — Brazilian Real' },
  { code: 'CAD', label: 'CAD — Canadian Dollar' },
];

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
