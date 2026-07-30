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
  'eventDetail.currencyLabel': 'Currency',
  'eventDetail.currencyOther': 'Other…',
  'eventDetail.currencyCustomPlaceholder': 'e.g. JPY',
  'eventDetail.currencyApply': 'Apply',
  'eventDetail.currencySaving': 'Saving…',

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
  'itemAssignment.amountAriaLabel': 'Amount owed by {name}',
  'itemAssignment.mismatch':
    'Amounts add up to {total}, not the item price of {expected}. You can still save — the server is the final judge.',

  // Extraction review (Phase 2)
  'extraction.title': 'Extract items from photo',
  'extraction.hint':
    'Reads the uploaded receipt image and proposes a list of items for you to review — nothing is saved until you confirm below.',
  'extraction.extractButton': 'Extract items from photo',
  'extraction.extracting': 'Extracting…',
  'extraction.manualFallbackHint': 'Manual capture below still works — add items by hand instead.',
  'extraction.reviewTitle': 'Review extracted items',
  'extraction.receiptTotalOnFile': 'Receipt total on file: {total}',
  'extraction.taxIncludedHint':
    'Tax/VAT of {total} was detected and has already been proportionally included in the item prices above — no one needs to be charged for it separately.',
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
  'extraction.currencyMismatch':
    'We detected this receipt is in {detected}, but this event is set to {current}. Switch the event to {detected}?',
  'extraction.currencySwitchButton': 'Switch to {detected}',
  'extraction.currencySwitching': 'Switching…',
  'extraction.currencyDismiss': 'Keep {current}',
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
  'balances.mixedCurrenciesHint':
    'Events use different currencies — totals below are a raw sum with no conversion applied.',
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

  // Backend-originated error messages (translated on the frontend only — see
  // i18n/apiMessages.js for the matcher that maps a raw `detail` string onto
  // one of these keys). Values here reproduce the backend's exact English
  // wording so EN users see identical text to before this catalog existed.
  'apiErrors.eventNotFound': 'Event {id} does not exist',
  'apiErrors.participantNotFound': 'Participant {id} does not exist',
  'apiErrors.itemNotFound': 'Item {id} does not exist',
  'apiErrors.receiptNotFound': 'Receipt {id} does not exist',
  'apiErrors.payerNotInEvent':
    'Participant {participantId} is not a participant of event {eventId}; add them via add_participant_to_event() first',
  'apiErrors.assigneeNotInEvent':
    'Participant {participantId} is not a participant of event {eventId}; cannot assign item {itemId} to them',
  'apiErrors.sharesSumMismatch': 'Item assignment shares must sum to 1.0, got {total}',
  'apiErrors.assignmentRequired': 'At least one assignment is required for item {itemId}',
  'apiErrors.duplicateParticipants': 'Duplicate participant ids in assignments for item {itemId}',
  'apiErrors.shareNotPositive': 'Share for participant {participantId} must be greater than 0, got {share}',
  'apiErrors.participantHasPaidReceipts':
    'Participant {participantId} has paid for one or more receipts and cannot be deleted (would corrupt payment history)',
  'apiErrors.participantHasAssignments':
    'Participant {participantId} has one or more item assignments and cannot be deleted (would corrupt consumption history)',
  'apiErrors.receiptNoImage': 'Receipt {receiptId} has no stored image; use manual item capture instead.',
  'apiErrors.uploadedFileEmpty': 'Uploaded file is empty',
  'apiErrors.extraction.unsupportedFormat':
    'This file format is not supported by automatic extraction (supported: JPEG, PNG, WEBP, GIF). Please use manual item capture.',
  'apiErrors.extraction.unreadableImage':
    "Could not read receipt image at '{path}'. Please retry with manual item capture.",
  'apiErrors.extraction.timeout':
    'The receipt extraction service took too long to respond. Try again, or use manual item capture.',
  'apiErrors.extraction.unavailable':
    'The receipt extraction service is unavailable right now. Please use manual item capture.',
  'apiErrors.extraction.emptyResponse':
    'The receipt extraction service returned an empty response. Please use manual item capture.',
  'apiErrors.extraction.unreadableResponse':
    'The receipt extraction service returned an unreadable response. Please use manual item capture.',
  'apiErrors.extraction.unexpectedFormat':
    'The receipt extraction service returned data in an unexpected format. Please use manual item capture.',
  'apiErrors.extraction.imageNotFound':
    "Receipt image not found at '{path}'. Please use manual item capture.",

  // Backend-originated warnings (vision.py's ExtractionResult.warnings[], via
  // the extraction proposal endpoint).
  'apiWarnings.itemsSumOverTotal':
    'Item prices sum to more than the receipt total ({itemsSum} > {receiptTotal}); please double-check the amounts before saving.',
  'apiWarnings.itemsSumUnderTotal':
    'Item prices sum to much less than the receipt total ({itemsSum} vs {receiptTotal}); some line items may be missing.',
};
