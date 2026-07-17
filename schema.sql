-- ReciboSplit: esquema inicial para Turso (libSQL / SQLite)
-- Fase 1: solo subida de imagen (sin reconocimiento automático)

CREATE TABLE participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    event_date TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Quiénes participan en cada evento (parrillada, día de viaje, etc.)
CREATE TABLE event_participants (
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    PRIMARY KEY (event_id, participant_id)
);

-- Un recibo subido (imagen) ligado a un evento y a quién pagó
CREATE TABLE receipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    image_path TEXT NOT NULL,
    paid_by INTEGER NOT NULL REFERENCES participants(id),
    total_amount REAL NOT NULL DEFAULT 0,
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Ítems capturados manualmente del recibo (fase 1: sin OCR/visión)
CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    price REAL NOT NULL,       -- precio total de la línea (ya incluye cantidad)
    quantity INTEGER NOT NULL DEFAULT 1  -- informativo, no se usa en el cálculo de balance
);

-- A quién(es) se le asigna el consumo de cada ítem, y en qué proporción
-- La suma de "share" para un mismo item_id debe ser 1.0
CREATE TABLE item_assignments (
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    share REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (item_id, participant_id)
);

-- Balance por evento: cuánto pagó vs. cuánto consumió cada participante
CREATE VIEW event_balances AS
SELECT
    ep.event_id,
    ep.participant_id,
    COALESCE(paid.total_paid, 0) AS total_paid,
    COALESCE(consumed.total_consumed, 0) AS total_consumed,
    COALESCE(paid.total_paid, 0) - COALESCE(consumed.total_consumed, 0) AS net_balance
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
) consumed ON consumed.event_id = ep.event_id AND consumed.participant_id = ep.participant_id;

-- Balance acumulado de todos los eventos (el número que realmente importa: quién debe en total)
CREATE VIEW overall_balances AS
SELECT
    participant_id,
    SUM(total_paid) AS total_paid_all_events,
    SUM(total_consumed) AS total_consumed_all_events,
    SUM(net_balance) AS total_net_balance
FROM event_balances
GROUP BY participant_id;
