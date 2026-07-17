// Collapsible in-app roadmap orienting a new user through the full manual-capture flow.
import { useState } from 'react';
import { useTranslation } from '../i18n/LanguageContext.jsx';

const STEP_KEYS = ['guide.step1', 'guide.step2', 'guide.step3', 'guide.step4', 'guide.step5', 'guide.step6', 'guide.step7'];

function GuideSteps() {
  const [open, setOpen] = useState(true);
  const { t } = useTranslation();

  return (
    <section className="guide-steps">
      <button
        type="button"
        className="guide-steps__toggle"
        aria-expanded={open}
        aria-controls="guide-steps-panel"
        onClick={() => setOpen((prev) => !prev)}
      >
        <span className="guide-steps__toggle-icon" aria-hidden="true">{open ? '−' : '+'}</span>
        {t('guide.toggle')}
      </button>

      {open ? (
        <div id="guide-steps-panel" className="guide-steps__panel">
          <ol className="guide-steps__list">
            {STEP_KEYS.map((key) => (
              <li key={key} className="guide-steps__item">
                {t(key)}
              </li>
            ))}
          </ol>
          <p className="guide-steps__note">{t('guide.note')}</p>
        </div>
      ) : null}
    </section>
  );
}

export default GuideSteps;
