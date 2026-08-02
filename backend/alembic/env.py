import os
import sys
sys.path.append(os.getcwd()) # ব্যাকএন্ড ডিরেক্টরি পাথ যুক্ত করা

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from dotenv import load_dotenv

# 🟢 1. Path Setup: Alembic-কে app ফোল্ডার চেনানোর জন্য
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# 🟢 2. Load .env
load_dotenv()

# 🟢 3. Import Base (যেখানে সব টেবিলের মেটাডেটা থাকে)
from app.core.database import Base
from app.core.models import User, Workspace
from app.models.user import User

config = context.config

# 🟢 4. Override Database URL (alembic.ini এর বদলে সরাসরি .env থেকে নিবে, হ্যাক প্রুফ)
config.set_main_option("sqlalchemy.url", os.getenv("SUPABASE_DB_URL"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 🟢 5. Target Metadata Set করা (এটাই টেবিল অটো-ক্রিয়েট করবে)
target_metadata = Base.metadata

# 🟢 ফাংশনটি Alembic-কে বলবে যে টেবিলগুলো কোডে নেই, সেগুলোতে হাত না দিতে
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and reflected and compare_to is None:
        return False
    return True

def run_migrations_offline() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object, # 🟢 (Safety Lock)
            compare_type=True # ডাটাবেসের টাইপ চেঞ্জ হলে ধরবে
        )

        with context.begin_transaction():
            context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
