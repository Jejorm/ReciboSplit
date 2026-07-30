// Lists a receipt's items with their current assignment summary and an expandable assign panel.
import { useState } from 'react';
import ItemAssignment from './ItemAssignment.jsx';
import StatusMessage from './StatusMessage.jsx';
import { formatCurrency } from '../utils.js';
import { useTranslation } from '../i18n/LanguageContext.jsx';

function ItemList({ items, eventParticipants, currency, onAssignmentsSaved }) {
  const { t } = useTranslation();
  const [expandedItemId, setExpandedItemId] = useState(null);

  if (items.length === 0) {
    return <StatusMessage kind="empty">{t('itemList.empty')}</StatusMessage>;
  }

  return (
    <ul className="item-list">
      {items.map((item) => {
        const assignments = item.assignments || [];
        const summary =
          assignments.length === 0
            ? t('itemList.unassigned')
            : assignments
                .map((assignment) =>
                  t('itemList.assignmentEntry', {
                    name: assignment.participant_name,
                    amount: formatCurrency(item.price * assignment.share, currency),
                  }),
                )
                .join(', ');
        const isExpanded = expandedItemId === item.id;

        return (
          <li key={item.id} className="item-list__row">
            <div className="item-list__summary">
              <span className="item-list__name">
                {item.description}
                {item.quantity && item.quantity > 1 ? t('itemList.quantitySuffix', { quantity: item.quantity }) : ''}
              </span>
              <span className="item-list__price">{formatCurrency(item.price, currency)}</span>
            </div>
            <p className="item-list__assignments">{summary}</p>
            <button
              type="button"
              className="btn btn--ghost btn--small"
              onClick={() => setExpandedItemId(isExpanded ? null : item.id)}
            >
              {isExpanded ? t('common.close') : t('itemList.assign')}
            </button>
            {isExpanded ? (
              <ItemAssignment
                item={item}
                eventParticipants={eventParticipants}
                currency={currency}
                onSaved={() => {
                  onAssignmentsSaved();
                  setExpandedItemId(null);
                }}
              />
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

export default ItemList;
