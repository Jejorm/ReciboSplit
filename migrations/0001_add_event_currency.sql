-- Adds a display-only currency code to events (no conversion, no FK to a currency table); balance math in schema.sql's views is unaffected.
ALTER TABLE events ADD COLUMN currency TEXT NOT NULL DEFAULT 'USD';
