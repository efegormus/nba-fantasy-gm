from alembic import context
from app.config import get_settings
from app.storage import Base, database

engine, _ = database(get_settings().database_url)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
