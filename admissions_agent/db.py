from sqlalchemy import JSON, Column, DateTime, Integer, MetaData, String, Table, create_engine
from sqlalchemy.sql import func

metadata = MetaData()

pending_actions = Table(
    "pending_actions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("action_id", String(255), unique=True, nullable=False),
    Column("thread_id", String(255), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


def init_db(db_url: str = "sqlite:///./data.db"):
    engine = create_engine(db_url)
    metadata.create_all(engine)
    return engine
