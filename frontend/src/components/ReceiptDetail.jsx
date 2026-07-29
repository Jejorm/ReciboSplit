// Item capture + assignment view for a single receipt.
import { useEffect, useState } from 'react';
import { getReceipt } from '../api.js';
import StatusMessage from './StatusMessage.jsx';
import ExtractionReview from './ExtractionReview.jsx';
import ItemForm from './ItemForm.jsx';
import ItemList from './ItemList.jsx';
import { formatCurrency } from '../utils.js';
import { useTranslation } from '../i18n/LanguageContext.jsx';
import { translateApiMessage } from '../i18n/apiMessages.js';

function ReceiptDetail({ receiptId, eventParticipants, fallbackTotal, onBack }) {
  const { t } = useTranslation();
  const [receipt, setReceipt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getReceipt(receiptId);
        if (!cancelled) setReceipt(data);
      } catch (loadError) {
        if (!cancelled) setError(loadError.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [receiptId]);

  async function refreshReceipt() {
    try {
      const data = await getReceipt(receiptId);
      setReceipt(data);
    } catch (refreshError) {
      setError(refreshError.message);
    }
  }

  if (loading) {
    return (
      <section className="page">
        <StatusMessage kind="loading">{t('receiptDetail.loading')}</StatusMessage>
      </section>
    );
  }

  if (error || !receipt) {
    return (
      <section className="page">
        <button type="button" className="btn btn--ghost" onClick={onBack}>
          {t('receiptDetail.backToEvent')}
        </button>
        <StatusMessage kind="error">{error ? translateApiMessage(error, t) : t('receiptDetail.notFound')}</StatusMessage>
      </section>
    );
  }

  const items = receipt.items || [];
  // items.price is already the full line total (quantity is informational only —
  // see schema.sql / event_balances view, which never multiplies by quantity).
  const itemsSum = items.reduce((sum, item) => sum + Number(item.price), 0);
  const receiptTotal = typeof receipt.total === 'number' ? receipt.total : fallbackTotal;
  const hasKnownTotal = receiptTotal !== null && receiptTotal !== undefined;
  const difference = hasKnownTotal ? itemsSum - receiptTotal : 0;
  const isMismatch = hasKnownTotal && Math.abs(difference) > 0.01;

  const reconcileDetail = t('receiptDetail.reconcile.detailBase', {
    sum: formatCurrency(itemsSum),
    total: formatCurrency(receiptTotal),
  });
  const reconcileSuffix = isMismatch
    ? t('receiptDetail.reconcile.mismatchSuffix', {
        direction: difference > 0 ? t('receiptDetail.reconcile.over') : t('receiptDetail.reconcile.under'),
        amount: formatCurrency(Math.abs(difference)),
      })
    : '.';

  return (
    <section className="page">
      <button type="button" className="btn btn--ghost" onClick={onBack}>
        {t('receiptDetail.backToEvent')}
      </button>

      <div className="page__intro">
        <h2 className="page__title">{t('receiptDetail.title', { id: receipt.id })}</h2>
        <p className="page__hint">{t('receiptDetail.hint')}</p>
      </div>

      <ExtractionReview receiptId={receiptId} onItemsAdded={refreshReceipt} />

      <div className="ledger-block">
        <h3 className="ledger-block__title">{t('receiptDetail.addItemTitle')}</h3>
        <ItemForm receiptId={receiptId} onItemAdded={refreshReceipt} />
      </div>

      <div className="ledger-block">
        <h3 className="ledger-block__title">{t('receiptDetail.itemsTitle')}</h3>
        {hasKnownTotal ? (
          <div
            className={`reconcile${isMismatch ? ' reconcile--mismatch' : ' reconcile--match'}`}
            role={isMismatch ? 'status' : undefined}
            aria-live={isMismatch ? 'polite' : undefined}
          >
            <p className="reconcile__headline">
              {isMismatch
                ? t('receiptDetail.reconcile.mismatchHeadline')
                : t('receiptDetail.reconcile.matchHeadline')}
            </p>
            <p className="reconcile__detail">
              {reconcileDetail}
              {reconcileSuffix}
            </p>
          </div>
        ) : null}
        <ItemList items={items} eventParticipants={eventParticipants} onAssignmentsSaved={refreshReceipt} />
      </div>
    </section>
  );
}

export default ReceiptDetail;
