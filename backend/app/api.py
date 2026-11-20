import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .analytics import category_totals
from .agent import GMTools, run_workflow
from .config import Settings, get_settings
from .demo import demo_snapshot
from .providers import parse_import
from .schemas import LeagueSetup, Mode, Snapshot
from .service import LeagueService
from .storage import database
from .run_history import RunHistory


class AgentRequest(BaseModel):
    question: str = Field(
        default="Review my waiver, trade and news opportunities", min_length=1, max_length=2000
    )
    use_local_ai: bool = False


class ImportRequest(BaseModel):
    format: str
    text: str = Field(max_length=5_000_000)
    metadata: dict | None = None


def create_app(settings: Settings | None = None, sessions=None) -> FastAPI:
    settings = settings or get_settings()
    if sessions is None:
        Path("data").mkdir(exist_ok=True)
        _, sessions = database(settings.database_url)
    service = LeagueService(sessions, settings)
    history = RunHistory(sessions)

    @asynccontextmanager
    async def lifespan(app):
        if len(settings.local_api_token) < 32:
            raise RuntimeError(
                "Set LOCAL_API_TOKEN to a randomly generated token of at least 32 characters in .env"
            )
        yield

    app = FastAPI(title="Fantasy NBA GM", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Authorization", "Content-Type"],
    )

    def authorized(request: Request, authorization: str = Header(default="")):
        if (
            request.headers.get("origin")
            and request.headers["origin"] not in settings.allowed_origins
        ):
            raise HTTPException(403, "Origin not allowed")
        if len(settings.local_api_token) < 32 or not secrets.compare_digest(
            authorization, "Bearer " + settings.local_api_token
        ):
            raise HTTPException(401, "Local pairing token required")

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/health")
    def health():
        return {"status": "ok", "yahoo_api": "disabled"}

    @app.get("/api/v1/league", dependencies=[Depends(authorized)])
    def league(mode: Mode = "real"):
        return service.status(mode)

    @app.put("/api/v1/league", dependencies=[Depends(authorized)])
    def update(setup: LeagueSetup, mode: Mode = "real"):
        service.save_setup(mode, setup)
        return service.status(mode)

    @app.post("/api/v1/imports/preview", dependencies=[Depends(authorized)])
    def preview(payload: ImportRequest, mode: Mode = "real"):
        snapshot = parse_import(payload.text, payload.format, payload.metadata)
        service.validate(mode, snapshot)
        return snapshot.model_dump(mode="json")

    @app.post("/api/v1/imports", dependencies=[Depends(authorized)])
    def commit(snapshot: Snapshot, mode: Mode = "real"):
        return service.import_snapshot(mode, snapshot)

    @app.post("/api/v1/demo", dependencies=[Depends(authorized)])
    def demo():
        return service.import_snapshot("demo", demo_snapshot())

    @app.get("/api/v1/team", dependencies=[Depends(authorized)])
    def team(mode: Mode = "real"):
        setup, record = service.setup(mode), service.latest(mode)
        if not setup.managed_team_id or not record:
            raise HTTPException(409, "Import a league and select your team in League Setup")
        roster = [
            p
            for p in Snapshot.model_validate(record.data).players
            if p.team_id == setup.managed_team_id
        ]
        return {"mode": mode, "team_id": setup.managed_team_id, "totals": category_totals(roster)}

    @app.post("/api/v1/agent/run", dependencies=[Depends(authorized)])
    def agent_run(payload: AgentRequest, mode: Mode = "real"):
        record = service.latest(mode)
        status = service.status(mode, record=record)
        snapshot = Snapshot.model_validate(record.data) if record else None
        report = run_workflow(
            GMTools(status, snapshot), settings, payload.question, payload.use_local_ai
        )
        scope = "demo" if mode == "demo" else "real:" + status["league_id"]
        saved = history.save(scope, record, status, payload.question, report)
        return {**report, "run_id": saved.id, "snapshot_id": saved.snapshot_id}

    @app.get("/api/v1/agent/runs", dependencies=[Depends(authorized)])
    def agent_runs(mode: Mode = "real", limit: int = Query(default=20, ge=1, le=100)):
        return {"runs": history.list(service.scope(mode), limit)}

    @app.get("/api/v1/agent/runs/{run_id}", dependencies=[Depends(authorized)])
    def agent_run_detail(run_id: int, mode: Mode = "real"):
        result = history.detail(service.scope(mode), run_id)
        if result is None:
            raise HTTPException(404, "Run not found in the selected league and mode")
        return result

    @app.get("/api/v1/recommendations", dependencies=[Depends(authorized)])
    def recommendations(mode: Mode = "real"):
        status = service.status(mode)
        return {
            "mode": mode,
            "league_id": status["league_id"],
            "freshness": status["freshness"],
            "last_successful_refresh": status["last_successful_refresh"],
            "items": [],
            "message": "Run the GM Workspace workflow to inspect provisional waiver/trade ideas and imported news.",
        }

    return app


app = create_app()
