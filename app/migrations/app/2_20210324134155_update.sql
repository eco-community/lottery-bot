-- upgrade --
ALTER TABLE "lottery" ALTER COLUMN "strike_date_eta" TYPE TIMESTAMPTZ;
-- downgrade --
ALTER TABLE "lottery" ALTER COLUMN "strike_date_eta" TYPE TIMESTAMPTZ;
