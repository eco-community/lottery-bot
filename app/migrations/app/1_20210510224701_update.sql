-- upgrade --
ALTER TABLE "lottery" ADD "number_of_winning_tickets" INT NOT NULL  DEFAULT 1;
-- downgrade --
ALTER TABLE "lottery" DROP COLUMN "number_of_winning_tickets";
