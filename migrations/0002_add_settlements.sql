-- Adds a settlements table (payments between participants to settle debts, fully or
-- partially) and folds it into event_balances / overall_balances so net_balance
-- accounts for cash settled outside the receipts themselves.

CREATE TABLE settlements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    from_participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    to_participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    amount REAL NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

DROP VIEW IF EXISTS overall_balances;
DROP VIEW IF EXISTS event_balances;

CREATE VIEW event_balances AS
SELECT
    ep.event_id,
    ep.participant_id,
    COALESCE(paid.total_paid, 0) AS total_paid,
    COALESCE(consumed.total_consumed, 0) AS total_consumed,
    COALESCE(settled_sent.total_settled_sent, 0) AS total_settled_sent,
    COALESCE(settled_received.total_settled_received, 0) AS total_settled_received,
    COALESCE(paid.total_paid, 0) - COALESCE(consumed.total_consumed, 0)
        + COALESCE(settled_sent.total_settled_sent, 0)
        - COALESCE(settled_received.total_settled_received, 0) AS net_balance
FROM event_participants ep
LEFT JOIN (
    SELECT event_id, paid_by AS participant_id, SUM(total_amount) AS total_paid
    FROM receipts
    GROUP BY event_id, paid_by
) paid ON paid.event_id = ep.event_id AND paid.participant_id = ep.participant_id
LEFT JOIN (
    SELECT r.event_id, ia.participant_id, SUM(i.price * ia.share) AS total_consumed
    FROM item_assignments ia
    JOIN items i ON i.id = ia.item_id
    JOIN receipts r ON r.id = i.receipt_id
    GROUP BY r.event_id, ia.participant_id
) consumed ON consumed.event_id = ep.event_id AND consumed.participant_id = ep.participant_id
LEFT JOIN (
    SELECT event_id, from_participant_id AS participant_id, SUM(amount) AS total_settled_sent
    FROM settlements
    GROUP BY event_id, from_participant_id
) settled_sent ON settled_sent.event_id = ep.event_id AND settled_sent.participant_id = ep.participant_id
LEFT JOIN (
    SELECT event_id, to_participant_id AS participant_id, SUM(amount) AS total_settled_received
    FROM settlements
    GROUP BY event_id, to_participant_id
) settled_received ON settled_received.event_id = ep.event_id AND settled_received.participant_id = ep.participant_id;

CREATE VIEW overall_balances AS
SELECT
    participant_id,
    SUM(total_paid) AS total_paid_all_events,
    SUM(total_consumed) AS total_consumed_all_events,
    SUM(total_settled_sent) AS total_settled_sent_all_events,
    SUM(total_settled_received) AS total_settled_received_all_events,
    SUM(net_balance) AS total_net_balance
FROM event_balances
GROUP BY participant_id;
