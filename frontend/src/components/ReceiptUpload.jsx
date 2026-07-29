// Multipart receipt upload form: image + payer + total. Guides the caller into item capture.
import { useState } from 'react';
import { uploadReceipt } from '../api.js';
import StatusMessage from './StatusMessage.jsx';
import { useTranslation } from '../i18n/LanguageContext.jsx';
import { translateApiMessage } from '../i18n/apiMessages.js';

function ReceiptUpload({ eventId, participants, onUploaded }) {
  const { t } = useTranslation();
  const [imageFile, setImageFile] = useState(null);
  const [payerParticipantId, setPayerParticipantId] = useState('');
  const [total, setTotal] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const canSubmit = imageFile !== null && payerParticipantId !== '' && total.trim() !== '' && !submitting;

  async function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError(null);
    try {
      const result = await uploadReceipt(eventId, {
        image: imageFile,
        payerParticipantId: Number(payerParticipantId),
        total: Number(total),
      });
      const uploadedTotal = Number(total);
      setImageFile(null);
      setPayerParticipantId('');
      setTotal('');
      onUploaded(result, uploadedTotal);
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (participants.length === 0) {
    return <StatusMessage kind="empty">{t('receiptUpload.noParticipants')}</StatusMessage>;
  }

  return (
    <form className="ledger-form" onSubmit={handleSubmit}>
      <label className="ledger-form__field">
        <span className="ledger-form__label">{t('receiptUpload.imageLabel')}</span>
        <input
          type="file"
          accept="image/*"
          onChange={(event) =>
            setImageFile(event.target.files && event.target.files[0] ? event.target.files[0] : null)
          }
          disabled={submitting}
        />
      </label>
      <label className="ledger-form__field">
        <span className="ledger-form__label">{t('receiptUpload.paidByLabel')}</span>
        <select
          value={payerParticipantId}
          onChange={(event) => setPayerParticipantId(event.target.value)}
          disabled={submitting}
        >
          <option value="">{t('receiptUpload.selectPayer')}</option>
          {participants.map((participant) => (
            <option key={participant.id} value={participant.id}>
              {participant.name}
            </option>
          ))}
        </select>
      </label>
      <label className="ledger-form__field">
        <span className="ledger-form__label">{t('receiptUpload.totalLabel')}</span>
        <input
          type="number"
          step="0.01"
          min="0"
          value={total}
          onChange={(event) => setTotal(event.target.value)}
          placeholder={t('common.amountPlaceholder')}
          disabled={submitting}
        />
      </label>
      <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
        {submitting ? t('receiptUpload.submitting') : t('receiptUpload.submit')}
      </button>
      {error ? <StatusMessage kind="error">{translateApiMessage(error, t)}</StatusMessage> : null}
    </form>
  );
}

export default ReceiptUpload;
