import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.database import get_db
from app.core.redis import get_redis_client
from app.core.security import hash_password
from app.models.crm import Customer
from app.models.security import Role, SystemUser
from main import app

# Setup in-memory sqlite for testing
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)

    def get_redis_override():
        return fake_redis

    app.dependency_overrides[get_db] = get_session_override
    app.dependency_overrides[get_redis_client] = get_redis_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_data")
def test_data_fixture(session: Session):
    # Create test roles
    role_admin = Role(role_name="admin")
    role_employee = Role(role_name="employee")
    session.add(role_admin)
    session.add(role_employee)
    session.commit()

    # Create admin user
    admin = SystemUser(
        full_name="Admin Test",
        email="admin@example.com",
        password_hash=hash_password("adminpass"),
        role_id=role_admin.role_id,
        is_active=True
    )
    session.add(admin)

    # Create customer
    customer = Customer(
        full_name="Customer Test",
        email="customer@example.com",
        password_hash=hash_password("customerpass"),
        is_registered=True,
        loyalty_points=10
    )
    session.add(customer)
    session.commit()
