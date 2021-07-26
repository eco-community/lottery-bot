-- upgrade --
ALTER TABLE "lottery" ADD "is_whitelisted" BOOL NOT NULL  DEFAULT False;
-- downgrade --
ALTER TABLE "lottery" DROP COLUMN "is_whitelisted";
