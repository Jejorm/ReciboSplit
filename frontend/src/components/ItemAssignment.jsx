// Assigns an item to one or more event participants with per-participant shares.
import { useState } from 'react';
import { setItemAssignments } from '../api.js';
import StatusMessage from './StatusMessage.jsx';
import { useTranslation } from '../i18n/LanguageContext.jsx';

function buildInitialShares(item) {
  const map = new Map();
  (item.assignments || []).forEach((assignment) => {
    map.set(assignment.participant_id, String(assignment.share));
  });
  return map;
}

function ItemAssignment({ item, eventParticipants, onSaved }) {
  const { t } = useTranslation();
  const [shares, setShares] = useState(() => buildInitialShares(item));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function toggleParticipant(participantId) {
    setShares((previous) => {
      const next = new Map(previous);
      if (next.has(participantId)) {
        next.delete(participantId);
      } else {
        next.set(participantId, '');
      }
      return next;
    });
  }

  function updateShare(participantId, value) {
    setShares((previous) => new Map(previous).set(participantId, value));
  }

  function handleEvenSplit() {
    const selectedIds =
      shares.size > 0 ? Array.from(shares.keys()) : eventParticipants.map((participant) => participant.id);
    if (selectedIds.length === 0) return;
    const evenShare = (1 / selectedIds.length).toFixed(4);
    setShares(new Map(selectedIds.map((id) => [id, evenShare])));
  }

  const totalShare = Array.from(shares.values()).reduce((sum, value) => sum + (Number.parseFloat(value) || 0), 0);
  const hasMismatch = shares.size > 0 && Math.abs(totalShare - 1) > 0.01;

  async function handleSave() {
    setSubmitting(true);
    setError(null);
    try {
      const payload = Array.from(shares.entries()).map(([participantId, share]) => ({
        participant_id: participantId,
        share: Number.parseFloat(share) || 0,
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
          const isChecked = shares.has(participant.id);
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
                <input
                  type="number"
                  step="0.0001"
                  min="0"
                  max="1"
                  className="assignment-panel__share"
                  value={shares.get(participant.id)}
                  onChange={(event) => updateShare(participant.id, event.target.value)}
                  disabled={submitting}
                />
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
          disabled={submitting || shares.size === 0}
        >
          {submitting ? t('itemAssignment.saving') : t('itemAssignment.save')}
        </button>
      </div>

      {hasMismatch ? (
        <StatusMessage kind="error">
          {t('itemAssignment.mismatch', { total: totalShare.toFixed(4) })}
        </StatusMessage>
      ) : null}
      {error ? <StatusMessage kind="error">{error}</StatusMessage> : null}
    </div>
  );
}

export default ItemAssignment;
