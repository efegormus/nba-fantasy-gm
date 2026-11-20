from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Configuration(Base):
    __tablename__ = "configuration"
    scope: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)


class ImportSnapshot(Base):
    __tablename__ = "import_snapshot"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String, index=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    data: Mapped[dict] = mapped_column(JSON)


class AgentRun(Base):
    __tablename__ = "agent_run"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String, index=True)
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("import_snapshot.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    question: Mapped[str] = mapped_column(String)
    context: Mapped[dict] = mapped_column(JSON)
    report: Mapped[dict] = mapped_column(JSON)


def database(url: str):
    engine = create_engine(
        url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {}
    )
    return engine, sessionmaker(engine, expire_on_commit=False)
