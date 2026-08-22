import pytest
from typing import Generator
from factories import UserFactory, CarbonLogFactory

@pytest.fixture(scope="session")
def deterministic_seed() -> int:
    return 1337

@pytest.fixture(scope="function")
def user_factory(deterministic_seed) -> UserFactory:
    return UserFactory(seed=deterministic_seed)

@pytest.fixture(scope="function")
def log_factory(deterministic_seed) -> CarbonLogFactory:
    return CarbonLogFactory(seed=deterministic_seed)

@pytest.fixture(scope="function")
def db_session() -> Generator[dict, None, None]:
    """Simulates an isolated database transaction with automatic cleanup."""
    session_store = {}
    yield session_store
    session_store.clear()  # Automatic cleanup execution
