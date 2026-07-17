// Top-level section switcher, styled as ledger file-folder tabs.
import { useTranslation } from '../i18n/LanguageContext.jsx';

const TABS = [
  { key: 'participants', labelKey: 'tabs.participants' },
  { key: 'events', labelKey: 'tabs.events' },
  { key: 'balances', labelKey: 'tabs.balances' },
];

function TabNav({ activeTab, onSelectTab }) {
  const { t } = useTranslation();

  return (
    <nav className="tab-nav" aria-label={t('tabs.ariaLabel')}>
      {TABS.map((tab) => (
        <button
          key={tab.key}
          type="button"
          className={`tab-nav__tab${activeTab === tab.key ? ' tab-nav__tab--active' : ''}`}
          onClick={() => onSelectTab(tab.key)}
          aria-current={activeTab === tab.key ? 'page' : undefined}
        >
          {t(tab.labelKey)}
        </button>
      ))}
    </nav>
  );
}

export default TabNav;
