// Lightweight custom i18n layer — no external dependency. Holds the active UI
// language in React context, persists it to localStorage, falls back to
// browser-language detection on first load, and exposes a t() lookup hook
// with {placeholder} interpolation and English fallback for missing keys.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import en from './en.js';
import es from './es.js';

const STORAGE_KEY = 'recibosplit.language';
const DICTIONARIES = { en, es };
const SUPPORTED_LANGUAGES = ['en', 'es'];

const LanguageContext = createContext(null);

function detectInitialLanguage() {
  if (typeof window !== 'undefined' && window.localStorage) {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (SUPPORTED_LANGUAGES.includes(stored)) return stored;
  }
  if (typeof navigator !== 'undefined' && navigator.language) {
    return navigator.language.toLowerCase().startsWith('es') ? 'es' : 'en';
  }
  return 'en';
}

function resolveTemplate(template, vars) {
  if (!vars) return template;
  return Object.keys(vars).reduce(
    (result, key) => result.replaceAll(`{${key}}`, String(vars[key])),
    template,
  );
}

function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(detectInitialLanguage);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEY, language);
    }
  }, [language]);

  const setLanguage = useCallback((next) => {
    setLanguageState(SUPPORTED_LANGUAGES.includes(next) ? next : 'en');
  }, []);

  const t = useCallback(
    (key, vars) => {
      const activeDictionary = DICTIONARIES[language] || DICTIONARIES.en;
      const template = activeDictionary[key] ?? DICTIONARIES.en[key] ?? key;
      return resolveTemplate(template, vars);
    },
    [language],
  );

  const value = useMemo(() => ({ language, setLanguage, t }), [language, setLanguage, t]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

function useTranslation() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useTranslation must be used within a LanguageProvider');
  }
  return context;
}

export { LanguageProvider, useTranslation };
