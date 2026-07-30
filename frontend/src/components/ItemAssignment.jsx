// Assigns an item to one or more event participants. The UI works entirely in
// money (the item's currency amount) — the backend's `share` fraction (0..1,
// must sum to 1.0) is only computed at the boundary, in handleSave.
import { useState } from 'react';
import { setItemAssignments } from '../api.js';
import StatusMessage from './StatusMessage.jsx';
import { useTranslation } from '../i18n/LanguageContext.jsx';
import { translateApiMessage } from '../i18n/apiMessages.js';
import { formatCurrency, getCurrencySymbol } from '../utils.js';

function buildInitialAmounts(item) {
  const map = new Map();
  (item.assignments || []).forEach((assignment) => {
    map.set(assignment.participant_id, (assignment.share * item.price).toFixed(2));
  });
  return map;
}

// Splits `price` evenly across `ids.length` participants in integer cents, so
// the amounts sum to EXACTLY `price` — no float rounding drift. Any leftover
// cent(s) from the integer division go to the first participant(s) in `ids`,
// the standard "split a bill fairly" algorithm.
function splitEvenly(price, ids) {
  const totalCents = Math.round((price || 0) * 100);
  const baseCents = Math.floor(totalCents / ids.length);
  const remainderCents = totalCents - baseCents * ids.length;
  return ids.map((id, index) => [id, ((baseCents + (index < remainderCents ? 1 : 0)) / 100).toFixed(2)]);
}

function ItemAssignment({ item, eventParticipants, currency = 'USD', onSaved }) {
  const { t } = useTranslation();
  const [amounts, setAmounts] = useState(() => buildInitialAmounts(item));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function toggleParticipant(participantId) {
    setAmounts((previous) => {
      const next = new Map(previous);
      if (next.has(participantId)) {
        next.delete(participantId);
      } else {
        next.set(participantId, '');
      }
      return next;
    });
  }

  function updateAmount(participantId, value) {
    setAmounts((previous) => new Map(previous).set(participantId, value));
  }

  function handleEvenSplit() {
    const selectedIds =
      amounts.size > 0 ? Array.from(amounts.keys()) : eventParticipants.map((participant) => participant.id);
    if (selectedIds.length === 0) return;
    setAmounts(new Map(splitEvenly(item.price, selectedIds)));
  }

  const totalAmount = Array.from(amounts.values()).reduce((sum, value) => sum + (Number.parseFloat(value) || 0), 0);
  const hasMismatch = amounts.size > 0 && Math.abs(totalAmount - item.price) > 0.01;

  async function handleSave() {
    setSubmitting(true);
    setError(null);
    try {
      const payload = Array.from(amounts.entries()).map(([participantId, amount]) => ({
        participant_id: participantId,
        // Full float division, not rounded — since the entered amounts sum
        // exactly to item.price in cents, the resulting shares sum within
        // float epsilon of 1.0, comfortably inside the backend's 1e-6 tolerance.
        share: item.price ? (Number.parseFloat(amount) || 0) / item.price : 0,
      }));
      const saved = await setItemAssignments(item.id, payload);
      onSaved(saved);
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="assignment-panel">
      <ul className="assignment-panel__list">
        {eventParticipants.map((participant) => {
          const isChecked = amounts.has(participant.id);
          return (
            <li key={participant.id} className="assignment-panel__row">
              <label className="assignment-panel__checkbox">
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => toggleParticipant(participant.id)}
                  disabled={submitting}
                />
                {participant.name}
              </label>
              {isChecked ? (
                <span className="assignment-panel__amount">
                  <span className="assignment-panel__currency-prefix" aria-hidden="true">
                    {getCurrencySymbol(currency)}
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    className="assignment-panel__share"
                    aria-label={t('itemAssignment.amountAriaLabel', { name: participant.name })}
                    value={amounts.get(participant.id)}
                    onChange={(event) => updateAmount(participant.id, event.target.value)}
                    disabled={submitting}
                  />
                </span>
              ) : null}
            </li>
          );
        })}
      </ul>

      <div className="assignment-panel__actions">
        <button type="button" className="btn btn--ghost btn--small" onClick={handleEvenSplit} disabled={submitting}>
          {t('itemAssignment.evenSplit')}
        </button>
        <button
          type="button"
          className="btn btn--primary btn--small"
          onClick={handleSave}
          disabled={submitting || amounts.size === 0}
        >
          {submitting ? t('itemAssignment.saving') : t('itemAssignment.save')}
        </button>
      </div>

      {hasMismatch ? (
        <StatusMessage kind="error">
          {t('itemAssignment.mismatch', {
            total: formatCurrency(totalAmount, currency),
            expected: formatCurrency(item.price, currency),
          })}
        </StatusMessage>
      ) : null}
      {error ? <StatusMessage kind="error">{translateApiMessage(error, t)}</StatusMessage> : null}
    </div>
  );
}

export default ItemAssignment;
