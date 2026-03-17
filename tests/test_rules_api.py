"""Tests for rules management API."""

import pytest
from fastapi.testclient import TestClient

from risklens.api.main import app
from risklens.engine.rule_store import get_rule_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_rules():
    """Clear rules before each test."""
    rule_store = get_rule_store()
    rule_store.clear()
    yield
    rule_store.clear()


def test_list_rules_empty():
    """Test listing rules when none exist."""
    response = client.get("/api/v1/rules")
    assert response.status_code == 200
    assert response.json() == []


def test_create_rule():
    """Test creating a new rule."""
    rule_data = {
        "rule_id": "test_rule_001",
        "name": "Test High Risk Rule",
        "description": "Test rule for high risk alerts",
        "pattern_types": ["WASH_TRADING"],
        "conditions": {"score": {"gte": 0.8}},
        "action": "FREEZE",
        "priority": 100,
        "enabled": True,
    }

    response = client.post("/api/v1/rules", json=rule_data)
    assert response.status_code == 201
    data = response.json()
    assert data["rule_id"] == "test_rule_001"
    assert data["name"] == "Test High Risk Rule"
    assert data["action"] == "FREEZE"


def test_create_duplicate_rule():
    """Test creating a rule with duplicate ID."""
    rule_data = {
        "rule_id": "test_rule_001",
        "name": "Test Rule",
        "description": "Test",
        "pattern_types": ["WASH_TRADING"],
        "conditions": {},
        "action": "OBSERVE",
        "priority": 0,
        "enabled": True,
    }

    # Create first rule
    response = client.post("/api/v1/rules", json=rule_data)
    assert response.status_code == 201

    # Try to create duplicate
    response = client.post("/api/v1/rules", json=rule_data)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_get_rule():
    """Test getting a rule by ID."""
    # Create a rule first
    rule_data = {
        "rule_id": "test_rule_002",
        "name": "Test Rule",
        "description": "Test",
        "pattern_types": ["SANDWICH_ATTACK"],
        "conditions": {},
        "action": "WARN",
        "priority": 50,
        "enabled": True,
    }
    client.post("/api/v1/rules", json=rule_data)

    # Get the rule
    response = client.get("/api/v1/rules/test_rule_002")
    assert response.status_code == 200
    data = response.json()
    assert data["rule_id"] == "test_rule_002"
    assert data["action"] == "WARN"


def test_get_nonexistent_rule():
    """Test getting a rule that doesn't exist."""
    response = client.get("/api/v1/rules/nonexistent")
    assert response.status_code == 404


def test_update_rule():
    """Test updating an existing rule."""
    # Create a rule
    rule_data = {
        "rule_id": "test_rule_003",
        "name": "Original Name",
        "description": "Original",
        "pattern_types": ["WASH_TRADING"],
        "conditions": {},
        "action": "OBSERVE",
        "priority": 10,
        "enabled": True,
    }
    client.post("/api/v1/rules", json=rule_data)

    # Update the rule
    updated_data = {
        "rule_id": "test_rule_003",
        "name": "Updated Name",
        "description": "Updated",
        "pattern_types": ["WASH_TRADING", "ROUNDTRIP"],
        "conditions": {"score": {"gte": 0.5}},
        "action": "FREEZE",
        "priority": 200,
        "enabled": False,
    }
    response = client.put("/api/v1/rules/test_rule_003", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["action"] == "FREEZE"
    assert data["priority"] == 200
    assert data["enabled"] is False


def test_update_nonexistent_rule():
    """Test updating a rule that doesn't exist."""
    rule_data = {
        "rule_id": "nonexistent",
        "name": "Test",
        "description": "Test",
        "pattern_types": ["WASH_TRADING"],
        "conditions": {},
        "action": "OBSERVE",
        "priority": 0,
        "enabled": True,
    }
    response = client.put("/api/v1/rules/nonexistent", json=rule_data)
    assert response.status_code == 404


def test_update_rule_id_mismatch():
    """Test updating with mismatched rule IDs."""
    # Create a rule
    rule_data = {
        "rule_id": "test_rule_004",
        "name": "Test",
        "description": "Test",
        "pattern_types": ["WASH_TRADING"],
        "conditions": {},
        "action": "OBSERVE",
        "priority": 0,
        "enabled": True,
    }
    client.post("/api/v1/rules", json=rule_data)

    # Try to update with different ID in body
    updated_data = rule_data.copy()
    updated_data["rule_id"] = "different_id"
    response = client.put("/api/v1/rules/test_rule_004", json=updated_data)
    assert response.status_code == 400
    assert "mismatch" in response.json()["detail"]


def test_delete_rule():
    """Test deleting a rule."""
    # Create a rule
    rule_data = {
        "rule_id": "test_rule_005",
        "name": "Test",
        "description": "Test",
        "pattern_types": ["WASH_TRADING"],
        "conditions": {},
        "action": "OBSERVE",
        "priority": 0,
        "enabled": True,
    }
    client.post("/api/v1/rules", json=rule_data)

    # Delete the rule
    response = client.delete("/api/v1/rules/test_rule_005")
    assert response.status_code == 204

    # Verify it's gone
    response = client.get("/api/v1/rules/test_rule_005")
    assert response.status_code == 404


def test_delete_nonexistent_rule():
    """Test deleting a rule that doesn't exist."""
    response = client.delete("/api/v1/rules/nonexistent")
    assert response.status_code == 404


def test_list_rules_multiple():
    """Test listing multiple rules."""
    # Create multiple rules
    for i in range(3):
        rule_data = {
            "rule_id": f"test_rule_{i}",
            "name": f"Rule {i}",
            "description": "Test",
            "pattern_types": ["WASH_TRADING"],
            "conditions": {},
            "action": "OBSERVE",
            "priority": i * 10,
            "enabled": True,
        }
        client.post("/api/v1/rules", json=rule_data)

    # List all rules
    response = client.get("/api/v1/rules")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # Should be sorted by priority (descending)
    assert data[0]["priority"] == 20
    assert data[1]["priority"] == 10
    assert data[2]["priority"] == 0


def test_list_rules_enabled_only():
    """Test listing only enabled rules."""
    # Create enabled and disabled rules
    for i in range(3):
        rule_data = {
            "rule_id": f"test_rule_{i}",
            "name": f"Rule {i}",
            "description": "Test",
            "pattern_types": ["WASH_TRADING"],
            "conditions": {},
            "action": "OBSERVE",
            "priority": 0,
            "enabled": i % 2 == 0,  # Even indices are enabled
        }
        client.post("/api/v1/rules", json=rule_data)

    # List only enabled rules
    response = client.get("/api/v1/rules?enabled_only=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # Only rules 0 and 2
    assert all(rule["enabled"] for rule in data)
