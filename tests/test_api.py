"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from risklens.api.main import app
from risklens.db.models import DecisionRecord
from risklens.db.session import SessionLocal, drop_db, get_db, init_db
from risklens.models import ActionType, PatternType, RiskLevel


@pytest.fixture(scope="function")
def db_session() -> Session:
    """Create a fresh database session for each test."""
    # Setup: create tables
    init_db()
    
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Teardown: drop tables
        drop_db()


@pytest.fixture(scope="function")
def test_client(db_session: Session):
    """Create test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_health_check(test_client: TestClient) -> None:
    """Test health check endpoint."""
    response = test_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data


def test_evaluate_alert_success(test_client: TestClient, db_session: Session) -> None:
    """Test successful alert evaluation."""
    alert_data = {
        "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "chain": "ethereum",
        "pool": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
        "pair": "WETH/USDC",
        "time_window_sec": 300,
        "pattern_type": "WASH_TRADING",
        "score": 0.87,
        "features": {
            "counterparty_diversity": 2,
            "roundtrip_count": 15,
            "total_volume_usd": 125000,
            "self_trade_ratio": 0.93,
        },
        "evidence_samples": [
            {"tx_hash": "0xabc", "amount_usd": 50000},
            {"tx_hash": "0xdef", "amount_usd": 50000},
        ],
    }
    
    response = test_client.post("/api/v1/evaluate", json=alert_data)
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify response structure
    assert "decision_id" in data
    assert data["address"] == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
    assert data["action"] in ["OBSERVE", "WARN", "FREEZE", "ESCALATE"]
    assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert 0 <= data["confidence"] <= 1
    assert 0 <= data["risk_score"] <= 100
    assert len(data["rationale"]) > 0
    assert len(data["evidence_refs"]) > 0
    assert len(data["recommendations"]) > 0
    assert data["rule_version"] == "v1.0.0"
    
    # Verify database record was created
    decision_id = data["decision_id"]
    record = db_session.query(DecisionRecord).filter(
        DecisionRecord.decision_id == decision_id
    ).first()
    assert record is not None
    assert record.address == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"


def test_evaluate_alert_high_risk(test_client: TestClient, db_session: Session) -> None:
    """Test high-risk alert triggers FREEZE."""
    alert_data = {
        "address": "0xhighrisk",
        "time_window_sec": 300,
        "pattern_type": "WASH_TRADING",
        "score": 0.95,
        "features": {
            "counterparty_diversity": 1,
            "total_volume_usd": 500000,
            "roundtrip_count": 30,
            "self_trade_ratio": 0.98,
        },
    }
    
    response = test_client.post("/api/v1/evaluate", json=alert_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "FREEZE"
    assert data["risk_level"] in ["HIGH", "CRITICAL"]


def test_evaluate_alert_low_risk(test_client: TestClient, db_session: Session) -> None:
    """Test low-risk alert triggers OBSERVE."""
    alert_data = {
        "address": "0xlowrisk",
        "time_window_sec": 300,
        "pattern_type": "WASH_TRADING",
        "score": 0.3,
        "features": {
            "counterparty_diversity": 20,
            "total_volume_usd": 5000,
        },
    }
    
    response = test_client.post("/api/v1/evaluate", json=alert_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "OBSERVE"
    assert data["risk_level"] in ["LOW", "MEDIUM"]


def test_get_decision_success(test_client: TestClient, db_session: Session) -> None:
    """Test retrieving a decision by ID."""
    # First, create a decision
    alert_data = {
        "address": "0xtest",
        "time_window_sec": 300,
        "pattern_type": "WASH_TRADING",
        "score": 0.8,
    }
    
    create_response = test_client.post("/api/v1/evaluate", json=alert_data)
    assert create_response.status_code == 201
    decision_id = create_response.json()["decision_id"]
    
    # Retrieve the decision
    get_response = test_client.get(f"/api/v1/decisions/{decision_id}")
    
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["decision_id"] == decision_id
    assert data["address"] == "0xtest"


def test_get_decision_not_found(test_client: TestClient) -> None:
    """Test 404 when decision doesn't exist."""
    response = test_client.get("/api/v1/decisions/nonexistent")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_decisions_all(test_client: TestClient, db_session: Session) -> None:
    """Test listing all decisions."""
    # Create multiple decisions
    for i in range(5):
        alert_data = {
            "address": f"0xtest{i}",
            "time_window_sec": 300,
            "pattern_type": "WASH_TRADING",
            "score": 0.5 + i * 0.1,
        }
        response = test_client.post("/api/v1/evaluate", json=alert_data)
        assert response.status_code == 201
    
    # List all decisions
    response = test_client.get("/api/v1/decisions")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


def test_list_decisions_filter_by_address(test_client: TestClient, db_session: Session) -> None:
    """Test filtering decisions by address."""
    # Create decisions for different addresses
    addresses = ["0xaaa", "0xbbb", "0xaaa", "0xccc", "0xaaa"]
    for addr in addresses:
        alert_data = {
            "address": addr,
            "time_window_sec": 300,
            "pattern_type": "WASH_TRADING",
            "score": 0.7,
        }
        response = test_client.post("/api/v1/evaluate", json=alert_data)
        assert response.status_code == 201
    
    # Filter by address
    response = test_client.get("/api/v1/decisions?address=0xaaa")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    for decision in data:
        assert decision["address"] == "0xaaa"


def test_list_decisions_filter_by_risk_level(test_client: TestClient, db_session: Session) -> None:
    """Test filtering decisions by risk level."""
    # Create decisions with different risk levels
    scores = [0.3, 0.5, 0.8, 0.95]  # LOW, MEDIUM, HIGH, CRITICAL
    for score in scores:
        alert_data = {
            "address": f"0xtest{score}",
            "time_window_sec": 300,
            "pattern_type": "WASH_TRADING",
            "score": score,
            "features": {
                "counterparty_diversity": 2 if score > 0.7 else 10,
                "total_volume_usd": 200000 if score > 0.7 else 10000,
            },
        }
        response = test_client.post("/api/v1/evaluate", json=alert_data)
        assert response.status_code == 201
    
    # Filter by HIGH risk level
    response = test_client.get("/api/v1/decisions?risk_level=HIGH")
    
    assert response.status_code == 200
    data = response.json()
    for decision in data:
        assert decision["risk_level"] in ["HIGH", "CRITICAL"]


def test_list_decisions_filter_by_action(test_client: TestClient, db_session: Session) -> None:
    """Test filtering decisions by action."""
    # Create decisions with different actions
    scores = [0.3, 0.6, 0.9]  # OBSERVE, WARN, FREEZE
    for score in scores:
        alert_data = {
            "address": f"0xtest{score}",
            "time_window_sec": 300,
            "pattern_type": "WASH_TRADING",
            "score": score,
            "features": {
                "counterparty_diversity": 2 if score > 0.7 else 10,
                "total_volume_usd": 200000 if score > 0.7 else 10000,
            },
        }
        response = test_client.post("/api/v1/evaluate", json=alert_data)
        assert response.status_code == 201
    
    # Filter by FREEZE action
    response = test_client.get("/api/v1/decisions?action=FREEZE")
    
    assert response.status_code == 200
    data = response.json()
    for decision in data:
        assert decision["action"] == "FREEZE"


def test_list_decisions_pagination(test_client: TestClient, db_session: Session) -> None:
    """Test pagination of decision list."""
    # Create 10 decisions
    for i in range(10):
        alert_data = {
            "address": f"0xtest{i}",
            "time_window_sec": 300,
            "pattern_type": "WASH_TRADING",
            "score": 0.5,
        }
        response = test_client.post("/api/v1/evaluate", json=alert_data)
        assert response.status_code == 201
    
    # Get first 5
    response1 = test_client.get("/api/v1/decisions?limit=5&offset=0")
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1) == 5
    
    # Get next 5
    response2 = test_client.get("/api/v1/decisions?limit=5&offset=5")
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2) == 5
    
    # Verify no overlap
    ids1 = {d["decision_id"] for d in data1}
    ids2 = {d["decision_id"] for d in data2}
    assert len(ids1.intersection(ids2)) == 0


def test_evaluate_alert_invalid_pattern_type(test_client: TestClient) -> None:
    """Test validation error for invalid pattern type."""
    alert_data = {
        "address": "0xtest",
        "time_window_sec": 300,
        "pattern_type": "INVALID_PATTERN",
        "score": 0.8,
    }
    
    response = test_client.post("/api/v1/evaluate", json=alert_data)
    assert response.status_code == 422  # Validation error


def test_evaluate_alert_missing_required_fields(test_client: TestClient) -> None:
    """Test validation error for missing required fields."""
    alert_data = {
        "address": "0xtest",
        # Missing pattern_type, score, time_window_sec
    }
    
    response = test_client.post("/api/v1/evaluate", json=alert_data)
    assert response.status_code == 422  # Validation error


def test_evaluate_alert_invalid_score(test_client: TestClient) -> None:
    """Test validation error for invalid score."""
    alert_data = {
        "address": "0xtest",
        "time_window_sec": 300,
        "pattern_type": "WASH_TRADING",
        "score": 1.5,  # Invalid: must be 0-1
    }
    
    response = test_client.post("/api/v1/evaluate", json=alert_data)
    assert response.status_code == 422  # Validation error
