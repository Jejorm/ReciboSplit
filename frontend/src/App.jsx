// Root component. Owns which top-level section (tab) is active; each page manages its own data.
import { useState } from 'react';
import TabNav from './components/TabNav.jsx';
import GuideSteps from './components/GuideSteps.jsx';
import ParticipantsPage from './components/ParticipantsPage.jsx';
import EventsPage from './components/EventsPage.jsx';
import BalancesPage from './components/BalancesPage.jsx';
import { useTranslation } from './i18n/LanguageContext.jsx';

function LanguageSwitcher() {
  const { language, setLanguage, t } = useTranslation();
  const nextLanguage = language === 'en' ? 'es' : 'en';
  const label = language === 'en' ? t('language.switchToSpanish') : t('language.switchToEnglish');

  return (
    <button
      type="button"
      className="btn btn--ghost btn--small language-switcher"
      onClick={() => setLanguage(nextLanguage)}
      aria-label={label}
      title={label}
    >
      <svg
        className="language-switcher__icon"
        viewBox="0 0 24 24"
        width="18"
        height="18"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" />
        <line x1="3" y1="12" x2="21" y2="12" />
        <path d="M12 3c2.5 2.5 4 5.7 4 9s-1.5 6.5-4 9c-2.5-2.5-4-5.7-4-9s1.5-6.5 4-9z" />
      </svg>
      <span className="language-switcher__code">{t('language.code')}</span>
    </button>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState('participants');
  const { t } = useTranslation();

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__header-bar">
          <LanguageSwitcher />
        </div>
        <h1 className="app__title">ReciboSplit</h1>
        <p className="app__subtitle">{t('app.subtitle')}</p>
      </header>

      <GuideSteps />

      <TabNav activeTab={activeTab} onSelectTab={setActiveTab} />

      <main className="app__page">
        {activeTab === 'participants' ? <ParticipantsPage /> : null}
        {activeTab === 'events' ? <EventsPage /> : null}
        {activeTab === 'balances' ? <BalancesPage /> : null}
      </main>
    </div>
  );
}

export default App;
