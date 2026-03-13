"""Tests for CLI module."""

from typer.testing import CliRunner

from risklens.cli import app

runner = CliRunner()


def test_cli_import():
    """Test that CLI module can be imported."""
    from risklens import cli

    assert cli.app is not None


def test_version_command():
    """Test version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "RiskLens Platform" in result.stdout
    assert "v1.0.0" in result.stdout


def test_db_check_command_help():
    """Test db check command shows help."""
    result = runner.invoke(app, ["db", "check", "--help"])
    assert result.exit_code == 0
    assert "Check database connection" in result.stdout


def test_serve_command_help():
    """Test serve command shows help."""
    result = runner.invoke(app, ["serve", "--help"], color=False)
    assert result.exit_code == 0
    assert "Start the FastAPI server" in result.stdout
    assert "host" in result.stdout.lower()
    assert "port" in result.stdout.lower()


def test_db_init_command_help():
    """Test db init command shows help."""
    result = runner.invoke(app, ["db", "init", "--help"])
    assert result.exit_code == 0
    assert "Initialize database schema" in result.stdout
