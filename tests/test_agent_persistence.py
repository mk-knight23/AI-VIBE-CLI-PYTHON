"""Comprehensive tests for agent persistence module."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import orjson

from friday_ai.agent.persistence import PersistenceManager, SessionSnapshot
from friday_ai.client.response import TokenUsage


class TestSessionSnapshot:
    """Test SessionSnapshot dataclass."""

    def test_session_snapshot_initialization(self):
        """Test SessionSnapshot initialization."""
        snapshot = SessionSnapshot(
            session_id="test-session-123",
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, 12, 30, 0, tzinfo=UTC),
            turn_count=5,
            messages=[{"role": "user", "content": "Hello"}],
            total_usage=TokenUsage(prompt_tokens=10, completion_tokens=20),
        )
        assert snapshot.session_id == "test-session-123"
        assert snapshot.turn_count == 5
        assert len(snapshot.messages) == 1

    def test_session_snapshot_to_dict(self):
        """Test converting SessionSnapshot to dict."""
        snapshot = SessionSnapshot(
            session_id="test-session",
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, 12, 30, 0, tzinfo=UTC),
            turn_count=3,
            messages=[{"role": "user", "content": "test"}],
            total_usage=TokenUsage(prompt_tokens=100, completion_tokens=200),
        )
        data = snapshot.to_dict()

        assert data["session_id"] == "test-session"
        assert isinstance(data["created_at"], str)
        assert data["turn_count"] == 3
        assert data["total_usage"]["prompt_tokens"] == 100

    def test_session_snapshot_from_dict(self):
        """Test creating SessionSnapshot from dict."""
        data = {
            "session_id": "test-session",
            "created_at": "2024-01-01T12:00:00+00:00",
            "updated_at": "2024-01-01T12:30:00+00:00",
            "turn_count": 3,
            "messages": [{"role": "user", "content": "test"}],
            "total_usage": {"prompt_tokens": 100, "completion_tokens": 200},
        }
        snapshot = SessionSnapshot.from_dict(data)

        assert snapshot.session_id == "test-session"
        assert snapshot.turn_count == 3
        assert snapshot.total_usage.prompt_tokens == 100


class TestPersistenceManager:
    """Test PersistenceManager class."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory."""
        return tmp_path / "friday_data"

    @pytest.fixture
    def mock_data_dir(self, temp_data_dir):
        """Mock get_data_dir to return temp directory."""
        with patch("friday_ai.agent.persistence.get_data_dir", return_value=temp_data_dir):
            yield temp_data_dir

    @pytest.fixture
    def persistence_manager(self, mock_data_dir):
        """Create a PersistenceManager with mocked data directory."""
        return PersistenceManager()

    @pytest.fixture
    def sample_snapshot(self):
        """Create a sample SessionSnapshot for testing."""
        return SessionSnapshot(
            session_id="test-session-123",
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, 12, 30, 0, tzinfo=UTC),
            turn_count=5,
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
            total_usage=TokenUsage(prompt_tokens=100, completion_tokens=200),
        )

    def test_persistence_manager_initialization(self, persistence_manager, mock_data_dir):
        """Test PersistenceManager creates necessary directories."""
        assert persistence_manager.sessions_dir.exists()
        assert persistence_manager.checkpoints_dir.exists()
        assert persistence_manager.sessions_dir == mock_data_dir / "sessions"
        assert persistence_manager.checkpoints_dir == mock_data_dir / "checkpoints"

    def test_persistence_manager_lock_initialization(self, persistence_manager):
        """Test PersistenceManager initializes lock."""
        assert persistence_manager._lock is not None
        assert isinstance(persistence_manager._lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_save_session(self, persistence_manager, sample_snapshot):
        """Test saving a session snapshot."""
        await persistence_manager.save_session(sample_snapshot)

        file_path = persistence_manager.sessions_dir / f"{sample_snapshot.session_id}.json"
        assert file_path.exists()

    @pytest.mark.asyncio
    async def test_save_session_creates_valid_json(self, persistence_manager, sample_snapshot):
        """Test saved session contains valid JSON data."""
        await persistence_manager.save_session(sample_snapshot)

        file_path = persistence_manager.sessions_dir / f"{sample_snapshot.session_id}.json"
        with open(file_path, "rb") as f:
            data = orjson.loads(f.read())

        assert data["session_id"] == sample_snapshot.session_id
        assert data["turn_count"] == sample_snapshot.turn_count

    @pytest.mark.asyncio
    async def test_load_session(self, persistence_manager, sample_snapshot):
        """Test loading a session snapshot."""
        # First save
        await persistence_manager.save_session(sample_snapshot)

        # Then load
        loaded = await persistence_manager.load_session(sample_snapshot.session_id)

        assert loaded is not None
        assert loaded.session_id == sample_snapshot.session_id
        assert loaded.turn_count == sample_snapshot.turn_count
        assert len(loaded.messages) == len(sample_snapshot.messages)

    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, persistence_manager):
        """Test loading a session that doesn't exist returns None."""
        loaded = await persistence_manager.load_session("nonexistent-session")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_save_and_load_multiple_sessions(self, persistence_manager):
        """Test saving and loading multiple sessions."""
        sessions = [
            SessionSnapshot(
                session_id=f"session-{i}",
                created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2024, 1, 1, 12, i * 10, tzinfo=UTC),
                turn_count=i,
                messages=[],
                total_usage=TokenUsage(prompt_tokens=i * 10, completion_tokens=i * 20),
            )
            for i in range(1, 4)
        ]

        for session in sessions:
            await persistence_manager.save_session(session)

        # Load each session
        for session in sessions:
            loaded = await persistence_manager.load_session(session.session_id)
            assert loaded.session_id == session.session_id
            assert loaded.turn_count == session.turn_count

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, persistence_manager):
        """Test listing sessions when none exist."""
        sessions = await persistence_manager.list_sessions()
        assert sessions == []

    @pytest.mark.asyncio
    async def test_list_sessions(self, persistence_manager):
        """Test listing all sessions."""
        # Create multiple sessions with different timestamps
        snapshots = [
            SessionSnapshot(
                session_id="session-1",
                created_at=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
                updated_at=datetime(2024, 1, 1, 10, 30, 0, tzinfo=UTC),
                turn_count=1,
                messages=[],
                total_usage=TokenUsage(prompt_tokens=10, completion_tokens=20),
            ),
            SessionSnapshot(
                session_id="session-2",
                created_at=datetime(2024, 1, 1, 11, 0, 0, tzinfo=UTC),
                updated_at=datetime(2024, 1, 1, 11, 30, 0, tzinfo=UTC),
                turn_count=2,
                messages=[],
                total_usage=TokenUsage(prompt_tokens=20, completion_tokens=40),
            ),
            SessionSnapshot(
                session_id="session-3",
                created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
                updated_at=datetime(2024, 1, 1, 12, 30, 0, tzinfo=UTC),
                turn_count=3,
                messages=[],
                total_usage=TokenUsage(prompt_tokens=30, completion_tokens=60),
            ),
        ]

        for snapshot in snapshots:
            await persistence_manager.save_session(snapshot)

        sessions = await persistence_manager.list_sessions()

        assert len(sessions) == 3
        # Should be sorted by updated_at descending
        assert sessions[0]["session_id"] == "session-3"
        assert sessions[1]["session_id"] == "session-2"
        assert sessions[2]["session_id"] == "session-1"

    @pytest.mark.asyncio
    async def test_list_sessions_metadata_only(self, persistence_manager):
        """Test that list_sessions only returns metadata, not full messages."""
        snapshot = SessionSnapshot(
            session_id="test-session",
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, 12, 30, 0, tzinfo=UTC),
            turn_count=5,
            messages=[
                {"role": "user", "content": "A very long message that shouldn't be in metadata"},
                {"role": "assistant", "content": "Another long message"},
            ],
            total_usage=TokenUsage(prompt_tokens=100, completion_tokens=200),
        )

        await persistence_manager.save_session(snapshot)
        sessions = await persistence_manager.list_sessions()

        assert len(sessions) == 1
        # Metadata should not include messages
        assert "messages" not in sessions[0]
        assert sessions[0]["session_id"] == "test-session"
        assert sessions[0]["turn_count"] == 5

    @pytest.mark.asyncio
    async def test_save_checkpoint(self, persistence_manager, sample_snapshot):
        """Test saving a checkpoint."""
        checkpoint_id = await persistence_manager.save_checkpoint(sample_snapshot)

        assert checkpoint_id is not None
        assert sample_snapshot.session_id in checkpoint_id
        # Checkpoint file should exist
        checkpoint_path = persistence_manager.checkpoints_dir / f"{checkpoint_id}.json"
        assert checkpoint_path.exists()

    @pytest.mark.asyncio
    async def test_save_checkpoint_multiple(self, persistence_manager, sample_snapshot):
        """Test saving multiple checkpoints for same session."""
        checkpoint1 = await persistence_manager.save_checkpoint(sample_snapshot)
        # Small delay to ensure different timestamp
        await asyncio.sleep(0.01)
        checkpoint2 = await persistence_manager.save_checkpoint(sample_snapshot)

        assert checkpoint1 != checkpoint2
        assert (persistence_manager.checkpoints_dir / f"{checkpoint1}.json").exists()
        assert (persistence_manager.checkpoints_dir / f"{checkpoint2}.json").exists()

    @pytest.mark.asyncio
    async def test_load_checkpoint(self, persistence_manager, sample_snapshot):
        """Test loading a checkpoint."""
        checkpoint_id = await persistence_manager.save_checkpoint(sample_snapshot)
        loaded = await persistence_manager.load_checkpoint(checkpoint_id)

        assert loaded is not None
        assert loaded.session_id == sample_snapshot.session_id
        assert loaded.turn_count == sample_snapshot.turn_count

    @pytest.mark.asyncio
    async def test_load_nonexistent_checkpoint(self, persistence_manager):
        """Test loading a checkpoint that doesn't exist returns None."""
        loaded = await persistence_manager.load_checkpoint("nonexistent-checkpoint")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_concurrent_save_operations(self, persistence_manager):
        """Test concurrent save operations use lock correctly."""
        snapshots = [
            SessionSnapshot(
                session_id=f"concurrent-{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                turn_count=i,
                messages=[],
                total_usage=TokenUsage(prompt_tokens=i, completion_tokens=i * 2),
            )
            for i in range(10)
        ]

        # Save all concurrently
        await asyncio.gather(*[persistence_manager.save_session(s) for s in snapshots])

        # Verify all saved
        for snapshot in snapshots:
            loaded = await persistence_manager.load_session(snapshot.session_id)
            assert loaded is not None
            assert loaded.turn_count == snapshot.turn_count

    @pytest.mark.asyncio
    async def test_session_overwrite(self, persistence_manager):
        """Test that saving a session overwrites existing one."""
        snapshot1 = SessionSnapshot(
            session_id="test-session",
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            turn_count=1,
            messages=[{"role": "user", "content": "First"}],
            total_usage=TokenUsage(prompt_tokens=10, completion_tokens=20),
        )

        snapshot2 = SessionSnapshot(
            session_id="test-session",  # Same ID
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
            turn_count=2,
            messages=[{"role": "user", "content": "Second"}],
            total_usage=TokenUsage(prompt_tokens=20, completion_tokens=40),
        )

        await persistence_manager.save_session(snapshot1)
        await persistence_manager.save_session(snapshot2)

        loaded = await persistence_manager.load_session("test-session")
        assert loaded.turn_count == 2  # Should have snapshot2's data
        assert loaded.messages[0]["content"] == "Second"

    @pytest.mark.asyncio
    async def test_read_session_metadata_corrupted_file(self, persistence_manager, mock_data_dir):
        """Test handling of corrupted session files."""
        # Create a valid session
        valid_snapshot = SessionSnapshot(
            session_id="valid-session",
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, 12, 30, 0, tzinfo=UTC),
            turn_count=1,
            messages=[],
            total_usage=TokenUsage(prompt_tokens=10, completion_tokens=20),
        )
        await persistence_manager.save_session(valid_snapshot)

        # Create a corrupted file
        corrupted_file = persistence_manager.sessions_dir / "corrupted-session.json"
        corrupted_file.write_text("invalid json content")

        # List sessions should handle corrupted file gracefully
        sessions = await persistence_manager.list_sessions()
        # Should only return the valid session
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "valid-session"

    @pytest.mark.asyncio
    async def test_session_with_complex_messages(self, persistence_manager):
        """Test session with complex message structures."""
        snapshot = SessionSnapshot(
            session_id="complex-session",
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, 12, 30, 0, tzinfo=UTC),
            turn_count=3,
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi", "tool_calls": [{"id": "call_1", "type": "function"}]},
                {"role": "tool", "tool_call_id": "call_1", "content": "Result"},
            ],
            total_usage=TokenUsage(prompt_tokens=50, completion_tokens=100),
        )

        await persistence_manager.save_session(snapshot)
        loaded = await persistence_manager.load_session("complex-session")

        assert len(loaded.messages) == 3
        assert loaded.messages[1].get("tool_calls") is not None
        assert loaded.messages[2]["tool_call_id"] == "call_1"

    @pytest.mark.asyncio
    async def test_zero_turn_count_session(self, persistence_manager):
        """Test session with zero turn count."""
        snapshot = SessionSnapshot(
            session_id="zero-turns",
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            turn_count=0,
            messages=[],
            total_usage=TokenUsage(prompt_tokens=0, completion_tokens=0),
        )

        await persistence_manager.save_session(snapshot)
        loaded = await persistence_manager.load_session("zero-turns")

        assert loaded.turn_count == 0
        assert loaded.total_usage.prompt_tokens == 0


class TestPersistenceManagerIntegration:
    """Integration tests for PersistenceManager."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory."""
        return tmp_path / "friday_data"

    @pytest.fixture
    def persistence_manager(self, temp_data_dir):
        """Create a PersistenceManager with temp directory."""
        with patch("friday_ai.agent.persistence.get_data_dir", return_value=temp_data_dir):
            return PersistenceManager()

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, persistence_manager):
        """Test complete session lifecycle: create, save, list, load."""
        # Create and save session
        snapshot = SessionSnapshot(
            session_id="lifecycle-test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            turn_count=5,
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
            ],
            total_usage=TokenUsage(prompt_tokens=50, completion_tokens=100),
        )
        await persistence_manager.save_session(snapshot)

        # List sessions
        sessions = await persistence_manager.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "lifecycle-test"

        # Load session
        loaded = await persistence_manager.load_session("lifecycle-test")
        assert loaded.turn_count == 5
        assert len(loaded.messages) == 2

        # Create checkpoint
        checkpoint_id = await persistence_manager.save_checkpoint(snapshot)
        assert checkpoint_id is not None

        # Load checkpoint
        checkpoint = await persistence_manager.load_checkpoint(checkpoint_id)
        assert checkpoint.session_id == "lifecycle-test"

    @pytest.mark.asyncio
    async def test_session_persistence_across_manager_instances(self, temp_data_dir):
        """Test that sessions persist across different PersistenceManager instances."""
        snapshot = SessionSnapshot(
            session_id="persist-test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            turn_count=10,
            messages=[],
            total_usage=TokenUsage(prompt_tokens=100, completion_tokens=200),
        )

        # First instance saves
        with patch("friday_ai.agent.persistence.get_data_dir", return_value=temp_data_dir):
            manager1 = PersistenceManager()
            await manager1.save_session(snapshot)

        # Second instance loads
        with patch("friday_ai.agent.persistence.get_data_dir", return_value=temp_data_dir):
            manager2 = PersistenceManager()
            loaded = await manager2.load_session("persist-test")

        assert loaded is not None
        assert loaded.turn_count == 10
