// Optional pre-fill flow: extracts a proposed item list from the receipt photo via the
// vision API, lets the human edit/remove rows, then saves through the existing Phase 1
// items endpoint. Manual capture (ItemForm) is unaffected whether this is used or not.
import { useState } from 'react';
import { extractReceiptItems, addItems } from '../api.js';
import StatusMessage from './StatusMessage.jsx';
import { formatCurrency } from '../utils.js';
import { useTranslation } from '../i18n/LanguageContext.jsx';
import { translateApiMessage } from '../i18n/apiMessages.js';

function makeRowId() {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `row-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function ExtractionReview({ receiptId, onItemsAdded }) {
  const { t } = useTranslation();
  const [status, setStatus] = useState('idle'); // 'idle' | 'extracting' | 'reviewing'
  const [rows, setRows] = useState([]);
  const [receiptTotal, setReceiptTotal] = useState(null);
  const [warnings, setWarnings] = useState([]);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  async function handleExtract() {
    setStatus('extracting');
    setError(null);
    try {
      const result = await extractReceiptItems(receiptId);
      setRows(
        (result.items || []).map((item) => ({
          id: makeRowId(),
          description: item.description,
          price: String(item.price),
          quantity: item.quantity,
        }))
      );
      setReceiptTotal(
        typeof result.receipt_total === 'number' ? result.receipt_total : null
      );
      setWarnings(result.warnings || []);
      setStatus('reviewing');
    } catch (extractError) {
      setError(extractError.message);
      setStatus('idle');
    }
  }

  function handleDiscard() {
    setRows([]);
    setReceiptTotal(null);
    setWarnings([]);
    setError(null);
    setStatus('idle');
  }

  function updateRow(id, field, value) {
    setRows((current) => current.map((row) => (row.id === id ? { ...row, [field]: value } : row)));
  }

  function removeRow(id) {
    setRows((current) => current.filter((row) => row.id !== id));
  }

  const isRowValid = (row) => row.description.trim() !== '' && Number(row.price) > 0;
  const allRowsValid = rows.length > 0 && rows.every(isRowValid);
  const canSave = allRowsValid && !saving;

  async function handleSave() {
    if (!canSave) return;
    setSaving(true);
    setError(null);
    try {
      await addItems(
        receiptId,
        rows.map((row) => ({ name: row.description.trim(), price: Number(row.price) }))
      );
      handleDiscard();
      onItemsAdded();
    } catch (saveError) {
      setError(saveError.message);
      // The backend inserts items one by one, so a mid-list failure can leave
      // earlier rows already saved. Refresh the real item list so the user can
      // see what landed and prune those rows before retrying.
      onItemsAdded();
    } finally {
      setSaving(false);
    }
  }

  if (status === 'idle') {
    return (
      <div className="ledger-block">
        <h3 className="ledger-block__title">{t('extraction.title')}</h3>
        <p className="page__hint">{t('extraction.hint')}</p>
        <button type="button" className="btn btn--secondary" onClick={handleExtract}>
          {t('extraction.extractButton')}
        </button>
        {error ? (
          <>
            <StatusMessage kind="error">{translateApiMessage(error, t)}</StatusMessage>
            <p className="page__hint">{t('extraction.manualFallbackHint')}</p>
          </>
        ) : null}
      </div>
    );
  }

  if (status === 'extracting') {
    return (
      <div className="ledger-block">
        <h3 className="ledger-block__title">{t('extraction.title')}</h3>
        <button type="button" className="btn btn--secondary" disabled>
          {t('extraction.extracting')}
        </button>
      </div>
    );
  }

  return (
    <div className="ledger-block">
      <h3 className="ledger-block__title">{t('extraction.reviewTitle')}</h3>

      {receiptTotal !== null ? (
        <p className="receipt-hint">{t('extraction.receiptTotalOnFile', { total: formatCurrency(receiptTotal) })}</p>
      ) : null}

      {warnings.map((warning, index) => (
        <p key={index} className="receipt-hint receipt-hint--mismatch">
          {translateApiMessage(warning, t)}
        </p>
      ))}

      {rows.length === 0 ? (
        <StatusMessage kind="empty">{t('extraction.noRowsLeft')}</StatusMessage>
      ) : (
        <table className="ledger-table ledger-table--editable">
          <thead>
            <tr>
              <th>{t('extraction.table.description')}</th>
              <th>{t('extraction.table.price')}</th>
              <th>{t('extraction.table.qty')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>
                  <input
                    type="text"
                    aria-label={t('extraction.table.descriptionAriaLabel')}
                    value={row.description}
                    onChange={(event) => updateRow(row.id, 'description', event.target.value)}
                    disabled={saving}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    aria-label={t('extraction.table.priceAriaLabel')}
                    value={row.price}
                    onChange={(event) => updateRow(row.id, 'price', event.target.value)}
                    disabled={saving}
                  />
                </td>
                <td>{row.quantity}</td>
                <td>
                  <button
                    type="button"
                    className="btn btn--ghost btn--small"
                    onClick={() => removeRow(row.id)}
                    disabled={saving}
                  >
                    {t('common.remove')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p className="page__hint">{t('extraction.quantityHint')}</p>

      {rows.length > 0 && !allRowsValid ? (
        <p className="receipt-hint receipt-hint--mismatch">{t('extraction.rowsInvalidHint')}</p>
      ) : null}

      <div className="assignment-panel__actions">
        <button type="button" className="btn btn--secondary" onClick={handleSave} disabled={!canSave}>
          {saving
            ? t('extraction.saving')
            : t(rows.length === 1 ? 'extraction.addItemsButtonOne' : 'extraction.addItemsButtonOther', {
                count: rows.length,
              })}
        </button>
        <button type="button" className="btn btn--ghost" onClick={handleDiscard} disabled={saving}>
          {t('common.discard')}
        </button>
      </div>

      {error ? (
        <>
          <StatusMessage kind="error">{translateApiMessage(error, t)}</StatusMessage>
          <p className="page__hint">{t('extraction.partialSaveHint')}</p>
        </>
      ) : null}
    </div>
  );
}

export default ExtractionReview;
