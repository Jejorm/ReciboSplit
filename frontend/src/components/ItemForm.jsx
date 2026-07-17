// Adds a single line item (name + price) to a receipt.
import { useState } from 'react';
import { addItems } from '../api.js';
import StatusMessage from './StatusMessage.jsx';
import { useTranslation } from '../i18n/LanguageContext.jsx';

function ItemForm({ receiptId, onItemAdded }) {
  const { t } = useTranslation();
  const [name, setName] = useState('');
  const [price, setPrice] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const canSubmit = name.trim() !== '' && price.trim() !== '' && !submitting;

  async function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError(null);
    try {
      await addItems(receiptId, { name: name.trim(), price: Number(price) });
      setName('');
      setPrice('');
      onItemAdded();
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="ledger-form ledger-form--inline" onSubmit={handleSubmit}>
      <label className="ledger-form__field">
        <span className="ledger-form__label">{t('itemForm.nameLabel')}</span>
        <input
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder={t('itemForm.namePlaceholder')}
          disabled={submitting}
        />
      </label>
      <label className="ledger-form__field">
        <span className="ledger-form__label">{t('itemForm.priceLabel')}</span>
        <input
          type="number"
          step="0.01"
          min="0"
          value={price}
          onChange={(event) => setPrice(event.target.value)}
          placeholder={t('common.amountPlaceholder')}
          disabled={submitting}
        />
      </label>
      <button type="submit" className="btn btn--secondary" disabled={!canSubmit}>
        {submitting ? t('itemForm.submitting') : t('itemForm.submit')}
      </button>
      {error ? <StatusMessage kind="error">{error}</StatusMessage> : null}
    </form>
  );
}

export default ItemForm;
