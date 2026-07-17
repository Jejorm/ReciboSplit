// Signature "ledger stamp" badge — reads a net balance and stamps it as owed / owes / settled.
import { formatCurrency } from '../utils.js';
import { useTranslation } from '../i18n/LanguageContext.jsx';

function BalanceBadge({ value }) {
  const { t } = useTranslation();
  const number = Number(value) || 0;
  let label;
  let modifier;

  if (number > 0.005) {
    label = t('balanceBadge.owed', { amount: formatCurrency(number) });
    modifier = 'credit';
  } else if (number < -0.005) {
    label = t('balanceBadge.owes', { amount: formatCurrency(Math.abs(number)) });
    modifier = 'debit';
  } else {
    label = t('balanceBadge.settled');
    modifier = 'settled';
  }

  return <span className={`stamp stamp--${modifier}`}>{label}</span>;
}

export default BalanceBadge;
