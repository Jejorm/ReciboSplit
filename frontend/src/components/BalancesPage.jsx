// Balances tab: per-event balance table plus the overall cumulative balance across all events.
import { useEffect, useState } from 'react';
import {
  createSettlement,
  deleteAllData,
  deleteSettlement,
  getEventBalances,
  getEvents,
  getEventSettlements,
  getOverallBalances,
  getParticipants,
} from '../api.js';
import StatusMessage from './StatusMessage.jsx';
import BalanceBadge from './BalanceBadge.jsx';
import { formatCurrency } from '../utils.js';
import { useTranslation } from '../i18n/LanguageContext.jsx';
import { translateApiMessage } from '../i18n/apiMessages.js';

// True when a row carries some settlement history worth flagging in the net
// cell — small float noise (e.g. 1e-9 leftovers) should not trigger the hint.
function hasSettlementHistory(row, sentField, receivedField) {
  return Math.abs(Number(row[sentField]) || 0) > 0.005 || Math.abs(Number(row[receivedField]) || 0) > 0.005;
}

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

  const [eventSettlements, setEventSettlements] = useState([]);
  const [loadingEventSettlements, setLoadingEventSettlements] = useState(false);
  const [eventSettlementsError, setEventSettlementsError] = useState(null);

  const [settlementFrom, setSettlementFrom] = useState('');
  const [settlementTo, setSettlementTo] = useState('');
  const [settlementAmount, setSettlementAmount] = useState('');
  const [settlementNote, setSettlementNote] = useState('');
  const [creatingSettlement, setCreatingSettlement] = useState(false);
  const [createSettlementError, setCreateSettlementError] = useState(null);

  const [deletingSettlementId, setDeletingSettlementId] = useState(null);
  const [deleteSettlementError, setDeleteSettlementError] = useState(null);

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

  async function loadEventBalances(eventId) {
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

  async function loadEventSettlements(eventId) {
    setLoadingEventSettlements(true);
    setEventSettlementsError(null);
    try {
      const data = await getEventSettlements(eventId);
      setEventSettlements(data);
    } catch (error) {
      setEventSettlementsError(error.message);
    } finally {
      setLoadingEventSettlements(false);
    }
  }

  function resetSettlementForm() {
    setSettlementFrom('');
    setSettlementTo('');
    setSettlementAmount('');
    setSettlementNote('');
    setCreateSettlementError(null);
  }

  async function handleSelectEvent(eventId) {
    setSelectedEventId(eventId);
    resetSettlementForm();
    if (eventId === '') {
      setEventBalances([]);
      setEventSettlements([]);
      return;
    }
    await Promise.all([loadEventBalances(eventId), loadEventSettlements(eventId)]);
  }

  // Prefills the settlement form from a debtor row: pays the participant with
  // the largest positive net balance, for whichever amount is smaller of the
  // two (so the prefill never overpays either side). Purely a convenience —
  // the user can still edit every field before submitting.
  function handleSettleUp(debtorRow, creditorRow) {
    if (!creditorRow) return;
    const amount = Math.min(Math.abs(Number(debtorRow.net_balance)), Number(creditorRow.net_balance));
    setSettlementFrom(String(debtorRow.participant_id));
    setSettlementTo(String(creditorRow.participant_id));
    setSettlementAmount(amount.toFixed(2));
    setCreateSettlementError(null);
  }

  const canSubmitSettlement =
    settlementFrom !== '' &&
    settlementTo !== '' &&
    settlementFrom !== settlementTo &&
    Number(settlementAmount) > 0 &&
    !creatingSettlement;

  async function handleCreateSettlement(formEvent) {
    formEvent.preventDefault();
    if (!canSubmitSettlement) return;

    setCreatingSettlement(true);
    setCreateSettlementError(null);
    try {
      await createSettlement(selectedEventId, {
        from_participant_id: Number(settlementFrom),
        to_participant_id: Number(settlementTo),
        amount: Number(settlementAmount),
        note: settlementNote.trim() || undefined,
      });
      resetSettlementForm();
      await Promise.all([loadEventBalances(selectedEventId), loadEventSettlements(selectedEventId), refreshOverall()]);
    } catch (error) {
      setCreateSettlementError(error.message);
    } finally {
      setCreatingSettlement(false);
    }
  }

  async function handleDeleteSettlement(settlement) {
    const confirmed = window.confirm(
      t('settlements.confirmDelete', {
        from: settlement.from_name,
        to: settlement.to_name,
        amount: formatCurrency(settlement.amount, selectedEventCurrency),
      }),
    );
    if (!confirmed) return;

    setDeletingSettlementId(settlement.id);
    setDeleteSettlementError(null);
    try {
      await deleteSettlement(settlement.id);
      await Promise.all([loadEventBalances(selectedEventId), loadEventSettlements(selectedEventId), refreshOverall()]);
    } catch (error) {
      setDeleteSettlementError(error.message);
    } finally {
      setDeletingSettlementId(null);
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
      setEventSettlements([]);
      setEventSettlementsError(null);
      resetSettlementForm();
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

  // The participant currently owed the most in this event — the default
  // "pay to" target when prefilling the settlement form from a debtor row.
  const topCreditor = eventBalances.reduce((best, row) => {
    if (Number(row.net_balance) <= 0.005) return best;
    if (!best || Number(row.net_balance) > Number(best.net_balance)) return row;
    return best;
  }, null);

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
              {eventBalances.map((balance) => {
                const isDebtor = Number(balance.net_balance) < -0.005;
                const canSettleUp = isDebtor && topCreditor && topCreditor.participant_id !== balance.participant_id;
                return (
                  <tr key={balance.participant_id}>
                    <td>{balance.participant_name}</td>
                    <td>{formatCurrency(balance.total_paid, selectedEventCurrency)}</td>
                    <td>{formatCurrency(balance.total_consumed, selectedEventCurrency)}</td>
                    <td>
                      <div className="net-cell">
                        <BalanceBadge value={balance.net_balance} currency={selectedEventCurrency} />
                        {canSettleUp ? (
                          <button
                            type="button"
                            className="btn btn--ghost btn--small"
                            onClick={() => handleSettleUp(balance, topCreditor)}
                          >
                            {t('settlements.settleUpButton')}
                          </button>
                        ) : null}
                      </div>
                      {hasSettlementHistory(balance, 'total_settled_sent', 'total_settled_received') ? (
                        <span className="net-hint">{t('balances.table.netIncludesPayments')}</span>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : null}
      </div>

      {selectedEventId !== '' && !loadingEventBalances && !eventBalancesError && eventBalances.length > 0 ? (
        <div className="ledger-block">
          <h3 className="ledger-block__title">{t('settlements.formTitle')}</h3>
          <form className="ledger-form" onSubmit={handleCreateSettlement}>
            <label className="ledger-form__field">
              <span className="ledger-form__label">{t('settlements.fromLabel')}</span>
              <select
                value={settlementFrom}
                onChange={(event) => setSettlementFrom(event.target.value)}
                disabled={creatingSettlement}
              >
                <option value="">{t('settlements.selectParticipant')}</option>
                {eventBalances.map((balance) => (
                  <option key={balance.participant_id} value={balance.participant_id}>
                    {balance.participant_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="ledger-form__field">
              <span className="ledger-form__label">{t('settlements.toLabel')}</span>
              <select
                value={settlementTo}
                onChange={(event) => setSettlementTo(event.target.value)}
                disabled={creatingSettlement}
              >
                <option value="">{t('settlements.selectParticipant')}</option>
                {eventBalances.map((balance) => (
                  <option key={balance.participant_id} value={balance.participant_id}>
                    {balance.participant_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="ledger-form__field">
              <span className="ledger-form__label">{t('settlements.amountLabel')}</span>
              <input
                type="number"
                step="0.01"
                min="0"
                value={settlementAmount}
                onChange={(event) => setSettlementAmount(event.target.value)}
                placeholder={t('common.amountPlaceholder')}
                disabled={creatingSettlement}
              />
            </label>
            <label className="ledger-form__field">
              <span className="ledger-form__label">{t('settlements.noteLabel')}</span>
              <input
                type="text"
                value={settlementNote}
                onChange={(event) => setSettlementNote(event.target.value)}
                placeholder={t('settlements.notePlaceholder')}
                disabled={creatingSettlement}
              />
            </label>
            <button type="submit" className="btn btn--secondary" disabled={!canSubmitSettlement}>
              {creatingSettlement ? t('settlements.submitting') : t('settlements.submit')}
            </button>
            {createSettlementError ? (
              <StatusMessage kind="error">{translateApiMessage(createSettlementError, t)}</StatusMessage>
            ) : null}
          </form>

          <h4 className="ledger-block__title">{t('settlements.historyTitle')}</h4>
          {loadingEventSettlements ? (
            <StatusMessage kind="loading">{t('settlements.loading')}</StatusMessage>
          ) : null}
          {!loadingEventSettlements && eventSettlementsError ? (
            <StatusMessage kind="error">{translateApiMessage(eventSettlementsError, t)}</StatusMessage>
          ) : null}
          {!loadingEventSettlements && !eventSettlementsError && eventSettlements.length === 0 ? (
            <StatusMessage kind="empty">{t('settlements.empty')}</StatusMessage>
          ) : null}
          {!loadingEventSettlements && !eventSettlementsError && eventSettlements.length > 0 ? (
            <ul className="ledger-list">
              {eventSettlements.map((settlement) => (
                <li key={settlement.id} className="ledger-list__row">
                  <span className="ledger-list__name">
                    {settlement.note
                      ? t('settlements.entryWithNote', {
                          from: settlement.from_name,
                          to: settlement.to_name,
                          amount: formatCurrency(settlement.amount, selectedEventCurrency),
                          note: settlement.note,
                        })
                      : t('settlements.entry', {
                          from: settlement.from_name,
                          to: settlement.to_name,
                          amount: formatCurrency(settlement.amount, selectedEventCurrency),
                        })}
                  </span>
                  <button
                    type="button"
                    className="btn btn--ghost btn--small"
                    onClick={() => handleDeleteSettlement(settlement)}
                    disabled={deletingSettlementId === settlement.id}
                  >
                    {deletingSettlementId === settlement.id ? t('common.deleting') : t('common.delete')}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {deleteSettlementError ? (
            <StatusMessage kind="error">{translateApiMessage(deleteSettlementError, t)}</StatusMessage>
          ) : null}
        </div>
      ) : null}

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
                    {hasSettlementHistory(
                      balance,
                      'total_settled_sent_all_events',
                      'total_settled_received_all_events',
                    ) ? (
                      <span className="net-hint">{t('balances.table.netIncludesPayments')}</span>
                    ) : null}
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
