-- Persist New Run passthrough metadata on the runs row so GET /runs can
-- display base_url / environment / branch without relying on S1 to echo them.

ALTER TABLE runs ADD COLUMN IF NOT EXISTS base_url TEXT;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS environment TEXT;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS branch TEXT;
