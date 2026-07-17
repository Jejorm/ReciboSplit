// English dictionary — source language. Keys are namespaced by component/area
// (e.g. "tabs.participants"). Values may contain {placeholder} interpolation
// tokens, resolved by the t() helper in LanguageContext.jsx.
export default {
  // App shell
  'app.subtitle': 'Split group expenses and track who owes whom, across every event.',

  // Language switcher
  'language.code': 'EN',
  'language.switchToSpanish': 'Switch language to Spanish',
  'language.switchToEnglish': 'Switch language to English',

  // Top-level tab navigation
  'tabs.ariaLabel': 'Main sections',
  'tabs.participants': 'Participants',
  'tabs.events': 'Events',
  'tabs.balances': 'Balances',

  // "How it works" guide
  'guide.toggle': 'How it works',
  'guide.step1': 'Add participants — the people splitting expenses (Participants tab)',
  'guide.step2': 'Create or pick an event — e.g. a cookout or trip (Events tab)',
  'guide.step3': 'Add those participants to the event',
  'guide.step4': 'Upload the receipt — its photo, who paid, and the total amount',
  'guide.step5': 'List each product with its price (quantity is optional, informational)',
  'guide.step6': 'Split each product among whoever consumed it',
  'guide.step7': 'See the total each person owes or is owed (Balances tab)',
  'guide.note': "Who paid and the total are what let the app compute who owes whom — don't skip them.",

  // Shared / common strings
  'common.delete': 'Delete',
  'common.deleting': 'Deleting…',
  'common.close': 'Close',
  'common.remove': 'Remove',
  'common.discard': 'Discard',
  'common.refresh': 'Refresh',
  'common.amountPlaceholder': '0.00',

  // Participants tab
  'participants.title': 'Participants',
  'participants.hint': 'Everyone who might owe or be owed, across every event.',
  'participants.form.nameLabel': 'Name',
  'participants.form.namePlaceholder': 'e.g. Alex Rivera',
  'participants.form.submit': 'Add participant',
  'participants.form.submitting': 'Adding…',
  'participants.loading': 'Loading participants…',
  'participants.empty': 'No participants yet. Add the first name above to start a ledger.',
  'participants.joined': 'joined {date}',
  'participants.confirmDelete': 'Delete participant "{name}"? This cannot be undone.',

  // Events tab
  'events.title': 'Events',
  'events.hint': 'A cookout, a trip, a shared tab — one ledger page per event.',
  'events.form.nameLabel': 'Event name',
  'events.form.namePlaceholder': 'e.g. Lake house weekend',
  'events.form.dateLabel': 'Date (optional)',
  'events.form.submit': 'Create event',
  'events.form.submitting': 'Creating…',
  'events.loading': 'Loading events…',
  'events.empty': 'No events yet. Create one above to start splitting a bill.',
  'events.confirmDelete': 'Delete event "{name}"? This also removes its receipts and items. This cannot be undone.',

  // Event detail
  'eventDetail.loading': 'Loading event…',
  'eventDetail.backToEvents': '← Back to events',
  'eventDetail.notFound': 'Event not found.',
  'eventDetail.participantsTitle': 'Participants in this event',
  'eventDetail.noParticipants': 'No one is linked yet. Add a participant below before uploading a receipt.',
  'eventDetail.loadingParticipants': 'Loading participants…',
  'eventDetail.addParticipantLabel': 'Add participant',
  'eventDetail.selectSomeone': 'Select someone…',
  'eventDetail.addToEvent': 'Add to event',
  'eventDetail.addingParticipant': 'Adding…',
  'eventDetail.everyoneLinked': 'Everyone is already linked to this event.',
  'eventDetail.uploadReceiptTitle': 'Upload a receipt',
  'eventDetail.receiptsTitle': 'Receipts for this event',
  'eventDetail.loadingReceipts': 'Loading receipts…',
  'eventDetail.noReceipts': 'No receipts uploaded yet for this event.',
  'eventDetail.receiptLabel': 'Receipt #{id} — paid by {payer}',

  // Receipt upload form
  'receiptUpload.noParticipants': 'Add at least one participant to this event before uploading a receipt.',
  'receiptUpload.imageLabel': 'Receipt image',
  'receiptUpload.paidByLabel': 'Paid by',
  'receiptUpload.selectPayer': 'Select payer…',
  'receiptUpload.totalLabel': 'Total amount',
  'receiptUpload.submit': 'Upload receipt',
  'receiptUpload.submitting': 'Uploading…',

  // Receipt detail
  'receiptDetail.loading': 'Loading receipt…',
  'receiptDetail.backToEvent': '← Back to event',
  'receiptDetail.notFound': 'Receipt not found.',
  'receiptDetail.title': 'Receipt #{id}',
  'receiptDetail.hint': 'Capture each line item, then assign it to whoever ate it.',
  'receiptDetail.addItemTitle': 'Add an item',
  'receiptDetail.itemsTitle': 'Items on this receipt',
  'receiptDetail.reconcile.matchHeadline': 'Items add up to the receipt total.',
  'receiptDetail.reconcile.mismatchHeadline': "Items don't add up yet",
  'receiptDetail.reconcile.detailBase': 'Items captured so far: {sum} of {total} total',
  'receiptDetail.reconcile.mismatchSuffix': ' — {direction} by {amount}. Add or fix items until they match.',
  'receiptDetail.reconcile.over': 'over',
  'receiptDetail.reconcile.under': 'under',

  // Item form (manual capture)
  'itemForm.nameLabel': 'Item',
  'itemForm.namePlaceholder': 'e.g. Cheeseburger',
  'itemForm.priceLabel': 'Price',
  'itemForm.submit': 'Add item',
  'itemForm.submitting': 'Adding…',

  // Item list
  'itemList.empty': 'No items captured yet. Add the first one above.',
  'itemList.unassigned': 'Unassigned',
  'itemList.assignmentEntry': '{name} ({amount})',
  'itemList.quantitySuffix': ' × {quantity}',
  'itemList.assign': 'Assign',

  // Item assignment panel
  'itemAssignment.evenSplit': 'Even split',
  'itemAssignment.save': 'Save assignment',
  'itemAssignment.saving': 'Saving…',
  'itemAssignment.mismatch': 'Shares add up to {total}, not 1.0. You can still save — the server is the final judge.',

  // Extraction review (Phase 2)
  'extraction.title': 'Extract items from photo',
  'extraction.hint':
    'Reads the uploaded receipt image and proposes a list of items for you to review — nothing is saved until you confirm below.',
  'extraction.extractButton': 'Extract items from photo',
  'extraction.extracting': 'Extracting…',
  'extraction.manualFallbackHint': 'Manual capture below still works — add items by hand instead.',
  'extraction.reviewTitle': 'Review extracted items',
  'extraction.receiptTotalOnFile': 'Receipt total on file: {total}',
  'extraction.noRowsLeft': 'No rows left to save. Discard, or extract again.',
  'extraction.table.description': 'Description',
  'extraction.table.price': 'Price',
  'extraction.table.qty': 'Qty',
  'extraction.table.descriptionAriaLabel': 'Item description',
  'extraction.table.priceAriaLabel': 'Item price',
  'extraction.quantityHint':
    "Quantity is shown for reference only — price already reflects the full line total for that quantity, and the save step below doesn't store quantity separately, so balances are unaffected.",
  'extraction.rowsInvalidHint':
    "Every row needs a description and a price greater than 0 before you can save — fix or remove the offending row.",
  'extraction.addItemsButtonOne': 'Add {count} item to receipt',
  'extraction.addItemsButtonOther': 'Add {count} items to receipt',
  'extraction.saving': 'Saving…',
  'extraction.partialSaveHint':
    'The save may have partially succeeded — check the items list below and remove any rows that were already added before retrying.',

  // Balances tab
  'balances.title': 'Balances',
  'balances.hint': 'Black ink means you are owed. Red ink means you owe.',
  'balances.byEventTitle': 'By event',
  'balances.loadingEvents': 'Loading events…',
  'balances.noEvents': 'No events yet — create one to see its balance.',
  'balances.selectEvent': 'Select an event…',
  'balances.loadingEventBalances': 'Loading balances…',
  'balances.noEventBalances': 'No balances yet for this event.',
  'balances.table.participant': 'Participant',
  'balances.table.paid': 'Paid',
  'balances.table.consumed': 'Consumed',
  'balances.table.net': 'Net',
  'balances.overallTitle': 'Overall, across every event',
  'balances.loadingOverall': 'Loading overall balances…',
  'balances.nothingToSettle': 'Nothing to settle yet.',
  'balances.dangerZone.title': 'Danger zone',
  'balances.dangerZone.hint': 'Permanently wipe every participant, event, receipt and balance.',
  'balances.dangerZone.deleteButton': 'Delete all data',
  'balances.dangerZone.deleting': 'Deleting…',
  'balances.dangerZone.confirmDeleteAll':
    'This deletes ALL participants, events, receipts and balances. This cannot be undone.',
  'balances.dangerZone.deleteSuccess': 'All data deleted.',

  // Balance badge
  'balanceBadge.owed': 'owed {amount}',
  'balanceBadge.owes': 'owes {amount}',
  'balanceBadge.settled': 'settled',
};
