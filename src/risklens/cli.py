"""Command-line interface for RiskLens Platform."""

import sys
from pathlib import Path

import typer
import uvicorn
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from risklens.config import get_settings
from risklens.db.session import engine

app = typer.Typer(
    name="risklens",
    help="RiskLens Platform - Production-grade risk control for Web3",
    add_completion=False,
)

db_app = typer.Typer(help="Database management commands")
app.add_typer(db_app, name="db")


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    # Find alembic.ini relative to project root
    project_root = Path(__file__).parent.parent.parent
    alembic_ini = project_root / "alembic.ini"

    if not alembic_ini.exists():
        typer.echo(f"Error: alembic.ini not found at {alembic_ini}", err=True)
        raise typer.Exit(1)

    alembic_cfg = Config(str(alembic_ini))
    return alembic_cfg


def check_db_connection() -> bool:
    """Check if database is reachable."""
    settings = get_settings()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        typer.echo(f"❌ Database connection failed: {e}", err=True)
        typer.echo(f"\nDatabase URL: {settings.database_url}", err=True)
        typer.echo("\nTroubleshooting:", err=True)
        typer.echo("  1. Check if PostgreSQL is running: docker-compose up -d", err=True)
        typer.echo("  2. Verify DATABASE_URL in .env matches docker-compose.yml", err=True)
        typer.echo("  3. Default port should be 5432 (not 5433)", err=True)
        return False


@db_app.command("init")
def db_init():
    """Initialize database schema (run migrations)."""
    typer.echo("🔍 Checking database connection...")

    if not check_db_connection():
        raise typer.Exit(1)

    typer.echo("✅ Database connection OK")
    typer.echo("🔄 Running migrations...")

    try:
        alembic_cfg = get_alembic_config()
        command.upgrade(alembic_cfg, "head")
        typer.echo("✅ Database initialized successfully")
    except Exception as e:
        typer.echo(f"❌ Migration failed: {e}", err=True)
        raise typer.Exit(1)


@db_app.command("check")
def db_check():
    """Check database connection."""
    typer.echo("🔍 Checking database connection...")

    if check_db_connection():
        typer.echo("✅ Database connection OK")
        settings = get_settings()
        typer.echo(f"   Connected to: {settings.database_url}")
    else:
        raise typer.Exit(1)


@app.command("serve")
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
    workers: int = typer.Option(1, help="Number of worker processes"),
):
    """Start the FastAPI server."""
    typer.echo("🔍 Pre-flight checks...")

    if not check_db_connection():
        typer.echo("\n⚠️  Database not reachable. Run 'risklens db init' first.", err=True)
        raise typer.Exit(1)

    typer.echo("✅ Pre-flight checks passed")
    typer.echo(f"🚀 Starting server on {host}:{port}")

    if reload and workers > 1:
        typer.echo(
            "⚠️  Warning: --reload and --workers > 1 are incompatible. Using --reload only.",
            err=True,
        )
        workers = 1

    uvicorn.run(
        "risklens.api.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
    )


@app.command("version")
def version():
    """Show version information."""
    typer.echo("RiskLens Platform v1.0.0")
    typer.echo("Phase 1: Decision Engine + FastAPI Service")


if __name__ == "__main__":
    app()
