-- upgrade --
ALTER TABLE "lottery" ADD "status" VARCHAR(10) NOT NULL  DEFAULT 'started';
ALTER TABLE "lottery" DROP COLUMN "is_finished";
ALTER TABLE "lottery" DROP COLUMN "has_winners_been_paid";
-- downgrade --
ALTER TABLE "lottery" ADD "is_finished" BOOL NOT NULL  DEFAULT False;
ALTER TABLE "lottery" ADD "has_winners_been_paid" BOOL NOT NULL  DEFAULT False;
ALTER TABLE "lottery" DROP COLUMN "status";
