import os
from dotenv import load_dotenv

from config import PROJECT_NAME

# load env variables
load_dotenv()


pg_user = os.getenv("POSTGRES_USER")
pg_password = os.getenv("POSTGRES_PASSWORD")
pg_db = os.getenv("POSTGRES_DB")


SENTRY_ENV_NAME = f"{PROJECT_NAME}_lottery_bot".casefold()
GUILD_INDEX = 0


TORTOISE_ORM = {
    "connections": {"default": f"postgres://{pg_user}:{pg_password}@localhost:5432/{pg_db}"},
    "apps": {
        "app": {
            "models": ["app.models", "aerich.models"],
        }
    },
}
