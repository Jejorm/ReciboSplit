// Translation catalog for backend-originated messages: HTTP error `detail`
// strings (surfaced as `Error.message` via api.js's handleResponse) and the
// vision extraction `warnings[]` entries. The backend (services.py, db.py,
// main.py, vision.py) is Phase 1/2-frozen and always answers in English —
// this module maps those known strings/patterns onto the frontend's own
// i18n keys (see en.js / es.js, `apiErrors.*` / `apiWarnings.*`) so they
// respect the active UI language, without touching the backend at all.
//
// Matching is against the literal backend wording, character-for-character.
// If any of those backend modules change their message text, this file's
// patterns need to be re-checked against them.
//
// Anything that doesn't match — an unknown/future backend message, a
// network-level error from the browser (e.g. "Failed to fetch"), or the
// frontend's own `Request failed with status {n}` fallback in api.js — is
// returned unchanged (graceful English fallback). Never throws; null,
// undefined, and non-string input are returned as-is.

const MATCHERS = [
  // --- db.py / value_error_to_http via main.py: "<Entity> <id> does not exist" (404) ---
  { pattern: /^Event (?<id>\d+) does not exist$/, key: 'apiErrors.eventNotFound' },
  { pattern: /^Participant (?<id>\d+) does not exist$/, key: 'apiErrors.participantNotFound' },
  { pattern: /^Item (?<id>\d+) does not exist$/, key: 'apiErrors.itemNotFound' },
  { pattern: /^Receipt (?<id>\d+) does not exist$/, key: 'apiErrors.receiptNotFound' },

  // --- db.py: create_receipt() payer-must-belong-to-event guard ---
  {
    pattern:
      /^Participant (?<participantId>\d+) is not a participant of event (?<eventId>\d+); add them via add_participant_to_event\(\) first$/,
    key: 'apiErrors.payerNotInEvent',
  },

  // --- db.py: assign_item() assignee-must-belong-to-event guard ---
  {
    pattern:
      /^Participant (?<participantId>\d+) is not a participant of event (?<eventId>\d+); cannot assign item (?<itemId>\d+) to them$/,
    key: 'apiErrors.assigneeNotInEvent',
  },

  // --- db.py: validate_shares() ---
  {
    pattern: /^Item assignment shares must sum to 1\.0, got (?<total>.+)$/,
    key: 'apiErrors.sharesSumMismatch',
  },

  // --- db.py: assign_item() ---
  {
    pattern: /^At least one assignment is required for item (?<itemId>\d+)$/,
    key: 'apiErrors.assignmentRequired',
  },
  {
    pattern: /^Duplicate participant ids in assignments for item (?<itemId>\d+)$/,
    key: 'apiErrors.duplicateParticipants',
  },
  {
    pattern: /^Share for participant (?<participantId>\d+) must be greater than 0, got (?<share>.+)$/,
    key: 'apiErrors.shareNotPositive',
  },

  // --- db.py: delete_participant() safe-deletion guard ---
  {
    pattern:
      /^Participant (?<participantId>\d+) has paid for one or more receipts and cannot be deleted \(would corrupt payment history\)$/,
    key: 'apiErrors.participantHasPaidReceipts',
  },
  {
    pattern:
      /^Participant (?<participantId>\d+) has one or more item assignments and cannot be deleted \(would corrupt consumption history\)$/,
    key: 'apiErrors.participantHasAssignments',
  },

  // --- main.py: extract_receipt() no-stored-image guard ---
  {
    pattern: /^Receipt (?<receiptId>\d+) has no stored image; use manual item capture instead\.$/,
    key: 'apiErrors.receiptNoImage',
  },

  // --- services.py: save_receipt_image() ---
  { pattern: /^Uploaded file is empty$/, key: 'apiErrors.uploadedFileEmpty' },

  // --- vision.py: ExtractionError (surfaced as a 502 `detail` by main.py's extract_receipt) ---
  {
    pattern:
      /^This file format is not supported by automatic extraction \(supported: JPEG, PNG, WEBP, GIF\)\. Please use manual item capture\.$/,
    key: 'apiErrors.extraction.unsupportedFormat',
  },
  {
    pattern: /^Could not read receipt image at '(?<path>.+)'\. Please retry with manual item capture\.$/,
    key: 'apiErrors.extraction.unreadableImage',
  },
  {
    pattern: /^The receipt extraction service took too long to respond\. Try again, or use manual item capture\.$/,
    key: 'apiErrors.extraction.timeout',
  },
  {
    pattern: /^The receipt extraction service is unavailable right now\. Please use manual item capture\.$/,
    key: 'apiErrors.extraction.unavailable',
  },
  {
    pattern: /^The receipt extraction service returned an empty response\. Please use manual item capture\.$/,
    key: 'apiErrors.extraction.emptyResponse',
  },
  {
    pattern: /^The receipt extraction service returned an unreadable response\. Please use manual item capture\.$/,
    key: 'apiErrors.extraction.unreadableResponse',
  },
  {
    pattern:
      /^The receipt extraction service returned data in an unexpected format\. Please use manual item capture\.$/,
    key: 'apiErrors.extraction.unexpectedFormat',
  },
  {
    pattern: /^Receipt image not found at '(?<path>.+)'\. Please use manual item capture\.$/,
    key: 'apiErrors.extraction.imageNotFound',
  },

  // --- vision.py: _apply_total_warnings() — ExtractionResult.warnings[] entries ---
  {
    pattern:
      /^Item prices sum to more than the receipt total \((?<itemsSum>[\d.]+) > (?<receiptTotal>[\d.]+)\); please double-check the amounts before saving\.$/,
    key: 'apiWarnings.itemsSumOverTotal',
  },
  {
    pattern:
      /^Item prices sum to much less than the receipt total \((?<itemsSum>[\d.]+) vs (?<receiptTotal>[\d.]+)\); some line items may be missing\.$/,
    key: 'apiWarnings.itemsSumUnderTotal',
  },
];

/**
 * Translate a backend-originated message (an HTTP error `detail` string, or
 * one entry of the extraction `warnings[]` array) into the active UI
 * language via the existing `t(key, vars)` i18n helper.
 *
 * Call this at RENDER time, not at catch/state-set time, so a message
 * already on screen re-translates automatically if the user switches
 * language afterwards — the raw English string is what should live in
 * component state.
 *
 * @param {unknown} message - the raw message to translate.
 * @param {(key: string, vars?: Record<string, unknown>) => string} t
 * @returns {unknown} the translated string, or `message` unchanged if it is
 *   not a string or does not match any known backend message pattern.
 */
export function translateApiMessage(message, t) {
  if (typeof message !== 'string') return message;

  for (const { pattern, key } of MATCHERS) {
    const match = message.match(pattern);
    if (match) {
      return t(key, match.groups || undefined);
    }
  }

  return message;
}
