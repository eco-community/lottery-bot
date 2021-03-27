-- upgrade --
CREATE TABLE IF NOT EXISTS "lottery" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "ticket_price" DECIMAL(15,2) NOT NULL  DEFAULT 10,
    "strike_date_eta" TIMESTAMPTZ NOT NULL,
    "strike_eth_block" INT NOT NULL,
    "winning_tickets" JSONB,
    "has_winners" BOOL NOT NULL  DEFAULT False,
    "status" VARCHAR(10) NOT NULL  DEFAULT 'started',
    "ticket_min_number" INT NOT NULL  DEFAULT 10000,
    "ticket_max_number" INT NOT NULL  DEFAULT 99000,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "lottery"."status" IS 'STARTED: started\nSTOP_SALES: stop_sales\nSTRIKED: striked\nENDED: ended';
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
