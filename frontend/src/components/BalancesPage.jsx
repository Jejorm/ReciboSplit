// Balances tab: per-event balance table plus the overall cumulative balance across all events.
import { useEffect, useState } from 'react';
import { deleteAllData, getEventBalances, getEvents, getOverallBalances, getParticipants } from '../api.js';
import StatusMessage from './StatusMessage.jsx';
import BalanceBadge from './BalanceBadge.jsx';
import { formatCurrency } from '../utils.js';
import { useTranslation } from '../i18n/LanguageContext.jsx';
import { translateApiMessage } from '../i18n/apiMessages.js';

function BalancesPage() {
  const { t } = useTranslation();
  const [participants, setParticipants] = useState([]);
  const [events, setEvents] = useState([]);
  const [loadingEvents, setLoadingEvents] = useState(true);
  const [eventsError, setEventsError] = useState(null);

  const [selectedEventId, setSelectedEventId] = useState('');
  const [eventBalances, setEventBalances] = useState([]);
  const [loadingEventBalances, setLoadingEventBalances] = useState(false);
  const [eventBalancesError, setEventBalancesError] = useState(null);

  const [overallBalances, setOverallBalances] = useState([]);
  const [loadingOverall, setLoadingOverall] = useState(true);
  const [overallError, setOverallError] = useState(null);

  const [deletingAll, setDeletingAll] = useState(false);
  const [deleteAllError, setDeleteAllError] = useState(null);
  const [deleteAllSuccess, setDeleteAllSuccess] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadInitial() {
      setLoadingEvents(true);
      setEventsError(null);
      setLoadingOverall(true);
      setOverallError(null);
      try {
        const [participantsData, eventsData, overallData] = await Promise.all([
          getParticipants(),
          getEvents(),
          getOverallBalances(),
        ]);
        if (!cancelled) {
          setParticipants(participantsData);
          setEvents(eventsData);
          setOverallBalances(overallData);
        }
      } catch (error) {
        if (!cancelled) {
          setEventsError(error.message);
          setOverallError(error.message);
        }
      } finally {
        if (!cancelled) {
          setLoadingEvents(false);
          setLoadingOverall(false);
        }
      }
    }

    loadInitial();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSelectEvent(eventId) {
    setSelectedEventId(eventId);
    if (eventId === '') {
      setEventBalances([]);
      return;
    }
    setLoadingEventBalances(true);
    setEventBalancesError(null);
    try {
      const data = await getEventBalances(eventId);
      setEventBalances(data);
    } catch (error) {
      setEventBalancesError(error.message);
    } finally {
      setLoadingEventBalances(false);
    }
  }

  async function refreshOverall() {
    setLoadingOverall(true);
    setOverallError(null);
    try {
      const data = await getOverallBalances();
      setOverallBalances(data);
    } catch (error) {
      setOverallError(error.message);
    } finally {
      setLoadingOverall(false);
    }
  }

  async function handleDeleteAllData() {
    const confirmed = window.confirm(t('balances.dangerZone.confirmDeleteAll'));
    if (!confirmed) return;

    setDeletingAll(true);
    setDeleteAllError(null);
    setDeleteAllSuccess(null);
    try {
      await deleteAllData();
      setSelectedEventId('');
      setEventBalances([]);
      setEventBalancesError(null);
      const [participantsData, eventsData, overallData] = await Promise.all([
        getParticipants(),
        getEvents(),
        getOverallBalances(),
      ]);
      setParticipants(participantsData);
      setEvents(eventsData);
      setOverallBalances(overallData);
      setDeleteAllSuccess(t('balances.dangerZone.deleteSuccess'));
    } catch (error) {
      setDeleteAllError(error.message);
    } finally {
      setDeletingAll(false);
    }
  }

  const hasData = participants.length > 0 || events.length > 0;
  const selectedEventCurrency =
    events.find((eventItem) => String(eventItem.id) === String(selectedEventId))?.currency || 'USD';
  const distinctCurrencies = new Set(events.map((eventItem) => eventItem.currency || 'USD'));
  const hasMixedCurrencies = distinctCurrencies.size > 1;

  return (
    <section className="page">
      <div className="page__intro">
        <h2 className="page__title">{t('balances.title')}</h2>
        <p className="page__hint">{t('balances.hint')}</p>
      </div>

      <div className="ledger-block">
        <h3 className="ledger-block__title">{t('balances.byEventTitle')}</h3>
        {loadingEvents ? <StatusMessage kind="loading">{t('balances.loadingEvents')}</StatusMessage> : null}
        {!loadingEvents && eventsError ? (
          <StatusMessage kind="error">{translateApiMessage(eventsError, t)}</StatusMessage>
        ) : null}
        {!loadingEvents && !eventsError && events.length === 0 ? (
          <StatusMessage kind="empty">{t('balances.noEvents')}</StatusMessage>
        ) : null}
        {!loadingEvents && !eventsError && events.length > 0 ? (
          <select value={selectedEventId} onChange={(event) => handleSelectEvent(event.target.value)}>
            <option value="">{t('balances.selectEvent')}</option>
            {events.map((eventItem) => (
              <option key={eventItem.id} value={eventItem.id}>
                {eventItem.name}
              </option>
            ))}
          </select>
        ) : null}

        {loadingEventBalances ? <StatusMessage kind="loading">{t('balances.loadingEventBalances')}</StatusMessage> : null}
        {!loadingEventBalances && eventBalancesError ? (
          <StatusMessage kind="error">{translateApiMessage(eventBalancesError, t)}</StatusMessage>
        ) : null}
        {!loadingEventBalances && !eventBalancesError && selectedEventId !== '' && eventBalances.length === 0 ? (
          <StatusMessage kind="empty">{t('balances.noEventBalances')}</StatusMessage>
        ) : null}
        {!loadingEventBalances && !eventBalancesError && eventBalances.length > 0 ? (
          <table className="ledger-table">
            <thead>
              <tr>
                <th>{t('balances.table.participant')}</th>
                <th>{t('balances.table.paid')}</th>
                <th>{t('balances.table.consumed')}</th>
                <th>{t('balances.table.net')}</th>
              </tr>
            </thead>
            <tbody>
              {eventBalances.map((balance) => (
                <tr key={balance.participant_id}>
                  <td>{balance.participant_name}</td>
                  <td>{formatCurrency(balance.total_paid, selectedEventCurrency)}</td>
                  <td>{formatCurrency(balance.total_consumed, selectedEventCurrency)}</td>
                  <td>
                    <BalanceBadge value={balance.net_balance} currency={selectedEventCurrency} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </div>

      <div className="ledger-block">
        <div className="ledger-block__header">
          <h3 className="ledger-block__title">{t('balances.overallTitle')}</h3>
          <button type="button" className="btn btn--ghost btn--small" onClick={refreshOverall} disabled={loadingOverall}>
            {t('common.refresh')}
          </button>
        </div>
        {!loadingOverall && !overallError && hasMixedCurrencies ? (
          <p className="page__hint">{t('balances.mixedCurrenciesHint')}</p>
        ) : null}
        {loadingOverall ? <StatusMessage kind="loading">{t('balances.loadingOverall')}</StatusMessage> : null}
        {!loadingOverall && overallError ? (
          <StatusMessage kind="error">{translateApiMessage(overallError, t)}</StatusMessage>
        ) : null}
        {!loadingOverall && !overallError && overallBalances.length === 0 ? (
          <StatusMessage kind="empty">{t('balances.nothingToSettle')}</StatusMessage>
        ) : null}
        {!loadingOverall && !overallError && overallBalances.length > 0 ? (
          <table className="ledger-table">
            <thead>
              <tr>
                <th>{t('balances.table.participant')}</th>
                <th>{t('balances.table.paid')}</th>
                <th>{t('balances.table.consumed')}</th>
                <th>{t('balances.table.net')}</th>
              </tr>
            </thead>
            <tbody>
              {overallBalances.map((balance) => (
                <tr key={balance.participant_id}>
                  <td>{balance.participant_name}</td>
                  <td>{formatCurrency(balance.total_paid_all_events)}</td>
                  <td>{formatCurrency(balance.total_consumed_all_events)}</td>
                  <td>
                    <BalanceBadge value={balance.total_net_balance} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </div>

      {hasData ? (
        <div className="danger-zone">
          <h3 className="danger-zone__title">{t('balances.dangerZone.title')}</h3>
          <p className="page__hint">{t('balances.dangerZone.hint')}</p>
          <button
            type="button"
            className="btn btn--danger"
            onClick={handleDeleteAllData}
            disabled={deletingAll}
          >
            {deletingAll ? t('balances.dangerZone.deleting') : t('balances.dangerZone.deleteButton')}
          </button>
          {deleteAllError ? <StatusMessage kind="error">{translateApiMessage(deleteAllError, t)}</StatusMessage> : null}
        </div>
      ) : null}
      {deleteAllSuccess ? <StatusMessage kind="success">{deleteAllSuccess}</StatusMessage> : null}
    </section>
  );
}

export default BalancesPage;
