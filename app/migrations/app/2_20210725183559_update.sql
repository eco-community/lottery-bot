-- upgrade --
ALTER TABLE "lottery" ADD "is_guaranteed" BOOL NOT NULL  DEFAULT False;
-- downgrade --
ALTER TABLE "lottery" DROP COLUMN "is_guaranteed";
