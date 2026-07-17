// Participants tab: lists everyone known to the ledger and lets you add new names.
import { useEffect, useState } from 'react';
import { createParticipant, deleteParticipant, getParticipants } from '../api.js';
import StatusMessage from './StatusMessage.jsx';
import { formatDate, toTitleCase } from '../utils.js';
import { useTranslation } from '../i18n/LanguageContext.jsx';

function ParticipantsPage() {
  const { t, language } = useTranslation();
  const [participants, setParticipants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [name, setName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const [deletingId, setDeletingId] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadParticipants() {
      setLoading(true);
      setLoadError(null);
      try {
        const data = await getParticipants();
        if (!cancelled) setParticipants(data);
      } catch (error) {
        if (!cancelled) setLoadError(error.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadParticipants();
    return () => {
      cancelled = true;
    };
  }, []);

  async function refreshParticipants() {
    try {
      const data = await getParticipants();
      setParticipants(data);
    } catch (error) {
      setLoadError(error.message);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const cleanName = toTitleCase(name);
    if (cleanName === '') return;

    setSubmitting(true);
    setSubmitError(null);
    try {
      await createParticipant(cleanName);
      setName('');
      await refreshParticipants();
    } catch (error) {
      setSubmitError(error.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(participant) {
    const confirmed = window.confirm(t('participants.confirmDelete', { name: participant.name }));
    if (!confirmed) return;

    setDeletingId(participant.id);
    setDeleteError(null);
    try {
      await deleteParticipant(participant.id);
      await refreshParticipants();
    } catch (error) {
      setDeleteError(error.message);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="page">
      <div className="page__intro">
        <h2 className="page__title">{t('participants.title')}</h2>
        <p className="page__hint">{t('participants.hint')}</p>
      </div>

      <form className="ledger-form" onSubmit={handleSubmit}>
        <label className="ledger-form__field">
          <span className="ledger-form__label">{t('participants.form.nameLabel')}</span>
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder={t('participants.form.namePlaceholder')}
            disabled={submitting}
          />
        </label>
        <button type="submit" className="btn btn--primary" disabled={submitting || name.trim() === ''}>
          {submitting ? t('participants.form.submitting') : t('participants.form.submit')}
        </button>
        {submitError ? <StatusMessage kind="error">{submitError}</StatusMessage> : null}
      </form>

      {loading ? <StatusMessage kind="loading">{t('participants.loading')}</StatusMessage> : null}
      {!loading && loadError ? <StatusMessage kind="error">{loadError}</StatusMessage> : null}
      {!loading && !loadError && participants.length === 0 ? (
        <StatusMessage kind="empty">{t('participants.empty')}</StatusMessage>
      ) : null}

      {!loading && !loadError && participants.length > 0 ? (
        <ul className="ledger-list">
          {participants.map((participant) => (
            <li key={participant.id} className="ledger-list__row">
              <span className="ledger-list__name">{participant.name}</span>
              <span className="ledger-list__meta">
                {t('participants.joined', { date: formatDate(participant.created_at, language) })}
              </span>
              <button
                type="button"
                className="btn btn--ghost btn--small"
                onClick={() => handleDelete(participant)}
                disabled={deletingId === participant.id}
              >
                {deletingId === participant.id ? t('common.deleting') : t('common.delete')}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {deleteError ? <StatusMessage kind="error">{deleteError}</StatusMessage> : null}
    </section>
  );
}

export default ParticipantsPage;
