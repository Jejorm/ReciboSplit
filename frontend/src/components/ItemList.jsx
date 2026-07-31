// Lists a receipt's items with their current assignment summary, an expandable
// assign panel, inline rename, and delete — each backed by its own confirm/loading
// state, following the same pattern as ParticipantsPage's delete flow.
import { useState } from 'react';
import ItemAssignment from './ItemAssignment.jsx';
import StatusMessage from './StatusMessage.jsx';
import { deleteItem, renameItem } from '../api.js';
import { formatCurrency } from '../utils.js';
import { useTranslation } from '../i18n/LanguageContext.jsx';
import { translateApiMessage } from '../i18n/apiMessages.js';

function ItemList({ items, eventParticipants, currency, onAssignmentsSaved }) {
  const { t } = useTranslation();
  const [expandedItemId, setExpandedItemId] = useState(null);

  const [editingItemId, setEditingItemId] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [renaming, setRenaming] = useState(false);
  const [renameError, setRenameError] = useState(null);

  const [deletingId, setDeletingId] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  if (items.length === 0) {
    return <StatusMessage kind="empty">{t('itemList.empty')}</StatusMessage>;
  }

  function startEditing(item) {
    setEditingItemId(item.id);
    setEditValue(item.description);
    setRenameError(null);
  }

  function cancelEditing() {
    setEditingItemId(null);
    setEditValue('');
    setRenameError(null);
  }

  async function handleRename(item) {
    const cleanDescription = editValue.trim();
    if (cleanDescription === '') return;

    setRenaming(true);
    setRenameError(null);
    try {
      await renameItem(item.id, cleanDescription);
      setEditingItemId(null);
      setEditValue('');
      onAssignmentsSaved();
    } catch (error) {
      setRenameError(error.message);
    } finally {
      setRenaming(false);
    }
  }

  async function handleDelete(item) {
    const confirmed = window.confirm(t('itemList.confirmDelete', { name: item.description }));
    if (!confirmed) return;

    setDeletingId(item.id);
    setDeleteError(null);
    try {
      await deleteItem(item.id);
      onAssignmentsSaved();
    } catch (error) {
      setDeleteError(error.message);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <>
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
          const isEditing = editingItemId === item.id;

          return (
            <li key={item.id} className="item-list__row">
              <div className="item-list__summary">
                {isEditing ? (
                  <input
                    type="text"
                    value={editValue}
                    onChange={(event) => setEditValue(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') handleRename(item);
                    }}
                    disabled={renaming}
                    autoFocus
                  />
                ) : (
                  <span className="item-list__name">
                    {item.description}
                    {item.quantity && item.quantity > 1
                      ? t('itemList.quantitySuffix', { quantity: item.quantity })
                      : ''}
                  </span>
                )}
                <span className="item-list__price">{formatCurrency(item.price, currency)}</span>
              </div>
              <p className="item-list__assignments">{summary}</p>

              {isEditing ? (
                <>
                  <button
                    type="button"
                    className="btn btn--primary btn--small"
                    onClick={() => handleRename(item)}
                    disabled={renaming || editValue.trim() === ''}
                  >
                    {renaming ? t('itemList.renaming') : t('itemList.save')}
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--small"
                    onClick={cancelEditing}
                    disabled={renaming}
                  >
                    {t('itemList.cancel')}
                  </button>
                </>
              ) : (
                <button type="button" className="btn btn--ghost btn--small" onClick={() => startEditing(item)}>
                  {t('itemList.rename')}
                </button>
              )}

              <button
                type="button"
                className="btn btn--ghost btn--small"
                onClick={() => setExpandedItemId(isExpanded ? null : item.id)}
              >
                {isExpanded ? t('common.close') : t('itemList.assign')}
              </button>

              <button
                type="button"
                className="btn btn--ghost btn--small"
                onClick={() => handleDelete(item)}
                disabled={deletingId === item.id}
              >
                {deletingId === item.id ? t('common.deleting') : t('common.delete')}
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

              {isEditing && renameError ? (
                <StatusMessage kind="error">{translateApiMessage(renameError, t)}</StatusMessage>
              ) : null}
            </li>
          );
        })}
      </ul>
      {deleteError ? <StatusMessage kind="error">{translateApiMessage(deleteError, t)}</StatusMessage> : null}
    </>
  );
}

export default ItemList;
