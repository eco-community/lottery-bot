-- upgrade --
CREATE TABLE IF NOT EXISTS "lottery" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "ticket_price" DECIMAL(15,2) NOT NULL  DEFAULT 10,
    "strike_date_eta" TIMESTAMPTZ,
    "strike_eth_block" INT NOT NULL,
    "winners" JSONB,
    "is_finished" BOOL NOT NULL  DEFAULT False,
    "has_winners_been_paid" BOOL NOT NULL  DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "lottery" IS 'Lottery table';
CREATE TABLE IF NOT EXISTS "user" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "balance" DECIMAL(15,2) NOT NULL  DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "user" IS 'User table';
CREATE TABLE IF NOT EXISTS "ticket" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "ticket_number" INT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "lottery_id" UUID NOT NULL REFERENCES "lottery" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_ticket_ticket__29ed4d" UNIQUE ("ticket_number", "lottery_id")
);
COMMENT ON TABLE "ticket" IS 'Many to many relationship between user and lottery';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(20) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "ticket" (
    "lottery_id" UUID NOT NULL REFERENCES "lottery" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
