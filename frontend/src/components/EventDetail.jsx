// Single event view: linked participants, add-participant, receipt upload, and the persistent
// list of receipts captured for this event (fetched from the API, so it survives reloads).
import { useEffect, useState } from 'react';
import { addParticipantToEvent, getEvent, getEventReceipts, getParticipants } from '../api.js';
import StatusMessage from './StatusMessage.jsx';
import ReceiptUpload from './ReceiptUpload.jsx';
import ReceiptDetail from './ReceiptDetail.jsx';
import { formatCurrency, formatDate } from '../utils.js';
import { useTranslation } from '../i18n/LanguageContext.jsx';

function EventDetail({ eventId, onBack }) {
  const { t, language } = useTranslation();
  const [event, setEvent] = useState(null);
  const [loadingEvent, setLoadingEvent] = useState(true);
  const [eventError, setEventError] = useState(null);

  const [allParticipants, setAllParticipants] = useState([]);
  const [loadingParticipants, setLoadingParticipants] = useState(true);
  const [participantsError, setParticipantsError] = useState(null);

  const [participantToAdd, setParticipantToAdd] = useState('');
  const [addingParticipant, setAddingParticipant] = useState(false);
  const [addParticipantError, setAddParticipantError] = useState(null);

  const [receipts, setReceipts] = useState([]);
  const [loadingReceipts, setLoadingReceipts] = useState(true);
  const [receiptsError, setReceiptsError] = useState(null);
  const [activeReceiptId, setActiveReceiptId] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadAll() {
      setLoadingEvent(true);
      setEventError(null);
      setLoadingParticipants(true);
      setParticipantsError(null);
      setLoadingReceipts(true);
      setReceiptsError(null);
      try {
        const [eventData, participantsData, receiptsData] = await Promise.all([
          getEvent(eventId),
          getParticipants(),
          getEventReceipts(eventId),
        ]);
        if (!cancelled) {
          setEvent(eventData);
          setAllParticipants(participantsData);
          setReceipts(receiptsData);
        }
      } catch (error) {
        if (!cancelled) {
          setEventError(error.message);
          setParticipantsError(error.message);
          setReceiptsError(error.message);
        }
      } finally {
        if (!cancelled) {
          setLoadingEvent(false);
          setLoadingParticipants(false);
          setLoadingReceipts(false);
        }
      }
    }

    loadAll();
    return () => {
      cancelled = true;
    };
  }, [eventId]);

  async function refreshEvent() {
    try {
      const eventData = await getEvent(eventId);
      setEvent(eventData);
    } catch (error) {
      setEventError(error.message);
    }
  }

  async function refreshReceipts() {
    setLoadingReceipts(true);
    setReceiptsError(null);
    try {
      const receiptsData = await getEventReceipts(eventId);
      setReceipts(receiptsData);
    } catch (error) {
      setReceiptsError(error.message);
    } finally {
      setLoadingReceipts(false);
    }
  }

  async function handleAddParticipant(formEvent) {
    formEvent.preventDefault();
    if (participantToAdd === '') return;

    setAddingParticipant(true);
    setAddParticipantError(null);
    try {
      await addParticipantToEvent(eventId, Number(participantToAdd));
      setParticipantToAdd('');
      await refreshEvent();
    } catch (error) {
      setAddParticipantError(error.message);
    } finally {
      setAddingParticipant(false);
    }
  }

  async function handleReceiptUploaded(receipt) {
    setActiveReceiptId(receipt.id);
    await refreshReceipts();
  }

  if (loadingEvent) {
    return (
      <section className="page">
        <StatusMessage kind="loading">{t('eventDetail.loading')}</StatusMessage>
      </section>
    );
  }

  if (eventError || !event) {
    return (
      <section className="page">
        <button type="button" className="btn btn--ghost" onClick={onBack}>
          {t('eventDetail.backToEvents')}
        </button>
        <StatusMessage kind="error">{eventError || t('eventDetail.notFound')}</StatusMessage>
      </section>
    );
  }

  const linkedIds = new Set(event.participants.map((participant) => participant.id));
  const availableParticipants = allParticipants.filter((participant) => !linkedIds.has(participant.id));

  if (activeReceiptId !== null) {
    const activeReceiptMeta = receipts.find((receipt) => receipt.id === activeReceiptId);
    return (
      <ReceiptDetail
        receiptId={activeReceiptId}
        eventParticipants={event.participants}
        fallbackTotal={activeReceiptMeta ? activeReceiptMeta.total_amount : null}
        onBack={() => setActiveReceiptId(null)}
      />
    );
  }

  return (
    <section className="page">
      <button type="button" className="btn btn--ghost" onClick={onBack}>
        {t('eventDetail.backToEvents')}
      </button>

      <div className="page__intro">
        <h2 className="page__title">{event.name}</h2>
        <p className="page__hint">{formatDate(event.event_date || event.created_at, language)}</p>
      </div>

      <div className="ledger-block">
        <h3 className="ledger-block__title">{t('eventDetail.participantsTitle')}</h3>
        {event.participants.length === 0 ? (
          <StatusMessage kind="empty">{t('eventDetail.noParticipants')}</StatusMessage>
        ) : (
          <ul className="chip-list">
            {event.participants.map((participant) => (
              <li key={participant.id} className="chip">
                {participant.name}
              </li>
            ))}
          </ul>
        )}

        {loadingParticipants ? <StatusMessage kind="loading">{t('eventDetail.loadingParticipants')}</StatusMessage> : null}
        {!loadingParticipants && participantsError ? (
          <StatusMessage kind="error">{participantsError}</StatusMessage>
        ) : null}

        {!loadingParticipants && !participantsError ? (
          <form className="ledger-form ledger-form--inline" onSubmit={handleAddParticipant}>
            <label className="ledger-form__field">
              <span className="ledger-form__label">{t('eventDetail.addParticipantLabel')}</span>
              <select
                value={participantToAdd}
                onChange={(event) => setParticipantToAdd(event.target.value)}
                disabled={addingParticipant || availableParticipants.length === 0}
              >
                <option value="">{t('eventDetail.selectSomeone')}</option>
                {availableParticipants.map((participant) => (
                  <option key={participant.id} value={participant.id}>
                    {participant.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="submit"
              className="btn btn--secondary"
              disabled={addingParticipant || participantToAdd === '' || availableParticipants.length === 0}
            >
              {addingParticipant ? t('eventDetail.addingParticipant') : t('eventDetail.addToEvent')}
            </button>
            {addParticipantError ? <StatusMessage kind="error">{addParticipantError}</StatusMessage> : null}
            {availableParticipants.length === 0 && allParticipants.length > 0 ? (
              <StatusMessage kind="empty">{t('eventDetail.everyoneLinked')}</StatusMessage>
            ) : null}
          </form>
        ) : null}
      </div>

      <div className="ledger-block">
        <h3 className="ledger-block__title">{t('eventDetail.uploadReceiptTitle')}</h3>
        <ReceiptUpload eventId={eventId} participants={event.participants} onUploaded={handleReceiptUploaded} />
      </div>

      <div className="ledger-block">
        <h3 className="ledger-block__title">{t('eventDetail.receiptsTitle')}</h3>
        {loadingReceipts ? <StatusMessage kind="loading">{t('eventDetail.loadingReceipts')}</StatusMessage> : null}
        {!loadingReceipts && receiptsError ? <StatusMessage kind="error">{receiptsError}</StatusMessage> : null}
        {!loadingReceipts && !receiptsError && receipts.length === 0 ? (
          <StatusMessage kind="empty">{t('eventDetail.noReceipts')}</StatusMessage>
        ) : null}
        {!loadingReceipts && !receiptsError && receipts.length > 0 ? (
          <ul className="ledger-list">
            {receipts.map((receipt) => (
              <li key={receipt.id} className="ledger-list__row ledger-list__row--clickable">
                <button type="button" className="ledger-list__link" onClick={() => setActiveReceiptId(receipt.id)}>
                  <span className="ledger-list__name">
                    {t('eventDetail.receiptLabel', { id: receipt.id, payer: receipt.payer_name })}
                  </span>
                  <span className="ledger-list__meta">
                    {formatCurrency(receipt.total_amount)} · {formatDate(receipt.uploaded_at, language)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}

export default EventDetail;
