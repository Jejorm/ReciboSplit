// Events tab: lists/creates events and drills into a single event's detail view.
import { useEffect, useState } from 'react';
import { createEvent, deleteEvent, getEvents } from '../api.js';
import StatusMessage from './StatusMessage.jsx';
import EventDetail from './EventDetail.jsx';
import { formatDate, toTitleCase } from '../utils.js';
import { useTranslation } from '../i18n/LanguageContext.jsx';

function EventsPage() {
  const { t, language } = useTranslation();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [name, setName] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const [selectedEventId, setSelectedEventId] = useState(null);

  const [deletingId, setDeletingId] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadEvents() {
      setLoading(true);
      setLoadError(null);
      try {
        const data = await getEvents();
        if (!cancelled) setEvents(data);
      } catch (error) {
        if (!cancelled) setLoadError(error.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadEvents();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    const cleanName = toTitleCase(name);
    if (cleanName === '') return;

    setSubmitting(true);
    setSubmitError(null);
    try {
      const created = await createEvent(cleanName, eventDate === '' ? undefined : eventDate);
      setName('');
      setEventDate('');
      const refreshed = await getEvents();
      setEvents(refreshed);
      setSelectedEventId(created.id);
    } catch (error) {
      setSubmitError(error.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(eventItem) {
    const confirmed = window.confirm(t('events.confirmDelete', { name: eventItem.name }));
    if (!confirmed) return;

    setDeletingId(eventItem.id);
    setDeleteError(null);
    try {
      await deleteEvent(eventItem.id);
      const refreshed = await getEvents();
      setEvents(refreshed);
    } catch (error) {
      setDeleteError(error.message);
    } finally {
      setDeletingId(null);
    }
  }

  if (selectedEventId !== null) {
    return <EventDetail eventId={selectedEventId} onBack={() => setSelectedEventId(null)} />;
  }

  return (
    <section className="page">
      <div className="page__intro">
        <h2 className="page__title">{t('events.title')}</h2>
        <p className="page__hint">{t('events.hint')}</p>
      </div>

      <form className="ledger-form" onSubmit={handleSubmit}>
        <label className="ledger-form__field">
          <span className="ledger-form__label">{t('events.form.nameLabel')}</span>
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder={t('events.form.namePlaceholder')}
            disabled={submitting}
          />
        </label>
        <label className="ledger-form__field">
          <span className="ledger-form__label">{t('events.form.dateLabel')}</span>
          <input
            type="date"
            value={eventDate}
            onChange={(event) => setEventDate(event.target.value)}
            disabled={submitting}
          />
        </label>
        <button type="submit" className="btn btn--primary" disabled={submitting || name.trim() === ''}>
          {submitting ? t('events.form.submitting') : t('events.form.submit')}
        </button>
        {submitError ? <StatusMessage kind="error">{submitError}</StatusMessage> : null}
      </form>

      {loading ? <StatusMessage kind="loading">{t('events.loading')}</StatusMessage> : null}
      {!loading && loadError ? <StatusMessage kind="error">{loadError}</StatusMessage> : null}
      {!loading && !loadError && events.length === 0 ? (
        <StatusMessage kind="empty">{t('events.empty')}</StatusMessage>
      ) : null}

      {!loading && !loadError && events.length > 0 ? (
        <ul className="ledger-list">
          {events.map((eventItem) => (
            <li key={eventItem.id} className="ledger-list__row ledger-list__row--clickable">
              <button type="button" className="ledger-list__link" onClick={() => setSelectedEventId(eventItem.id)}>
                <span className="ledger-list__name">{eventItem.name}</span>
                <span className="ledger-list__meta">
                  {formatDate(eventItem.event_date || eventItem.created_at, language)}
                </span>
              </button>
              <button
                type="button"
                className="btn btn--ghost btn--small"
                onClick={() => handleDelete(eventItem)}
                disabled={deletingId === eventItem.id}
              >
                {deletingId === eventItem.id ? t('common.deleting') : t('common.delete')}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {deleteError ? <StatusMessage kind="error">{deleteError}</StatusMessage> : null}
    </section>
  );
}

export default EventsPage;
