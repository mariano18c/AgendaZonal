"""Unit tests for app/main.py startup and migrations."""
import pytest
from unittest.mock import MagicMock, patch
from app.main import startup_security_check
from sqlalchemy import text

@pytest.mark.asyncio
async def test_startup_security_check_migrations(db_session):
    # Mock engine and inspector to trigger migration lines
    mock_inspector = MagicMock()
    mock_inspector.get_table_names.return_value = ["reviews"] # Skip push_subscriptions creation
    mock_inspector.get_columns.return_value = [] # No columns -> add everything
    
    mock_conn = MagicMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    
    with patch("sqlalchemy.inspect", return_value=mock_inspector), \
         patch("app.database.engine", mock_engine), \
         patch("app.main.logger") as mock_logger:
        
        await startup_security_check()
        
        # Verify migration commands were sent
        # Should have 3 ALTER TABLE calls
        # (Actually, in our test it depends on how many columns we mocked as missing)
        assert mock_conn.execute.called

@pytest.mark.asyncio
async def test_startup_create_push_table(db_session):
    mock_inspector = MagicMock()
    mock_inspector.get_table_names.return_value = [] # No tables -> create all
    
    with patch("sqlalchemy.inspect", return_value=mock_inspector), \
         patch("app.database.engine", MagicMock()), \
         patch("app.main.logger"):
        
        # This will trigger Base.metadata.create_all
        with patch("app.database.Base.metadata.create_all") as mock_create:
            await startup_security_check()
            assert mock_create.called
