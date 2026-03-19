"""Rule storage and management for dynamic rule configuration."""

import json
from pathlib import Path
from typing import Optional

from risklens.models import RuleDefinition


class RuleStore:
    """In-memory rule store with file persistence.

    This is a simple implementation for Phase 2. In production, you would
    use a database (PostgreSQL) or distributed config store (etcd, Consul).
    """

    def __init__(self, rules_file: Optional[str] = None):
        """Initialize rule store.

        Args:
            rules_file: Path to JSON file for persisting rules
        """
        self.rules_file = Path(rules_file) if rules_file else None
        self.rules: dict[str, RuleDefinition] = {}

        # Load rules from file if exists
        if self.rules_file and self.rules_file.exists():
            self._load_from_file()

    def _load_from_file(self):
        """Load rules from JSON file."""
        try:
            with open(self.rules_file) as f:
                data = json.load(f)
                for rule_data in data:
                    rule = RuleDefinition(**rule_data)
                    self.rules[rule.rule_id] = rule
        except Exception as e:
            raise RuntimeError(f"Failed to load rules from {self.rules_file}: {e}")

    def _save_to_file(self):
        """Save rules to JSON file."""
        if not self.rules_file:
            return

        try:
            self.rules_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.rules_file, "w") as f:
                data = [rule.model_dump(mode="json") for rule in self.rules.values()]
                json.dump(data, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save rules to {self.rules_file}: {e}")

    def create(self, rule: RuleDefinition) -> RuleDefinition:
        """Create a new rule.

        Args:
            rule: Rule definition

        Returns:
            Created rule

        Raises:
            ValueError: If rule with same ID already exists
        """
        if rule.rule_id in self.rules:
            raise ValueError(f"Rule with ID {rule.rule_id} already exists")

        self.rules[rule.rule_id] = rule
        self._save_to_file()
        return rule

    def get(self, rule_id: str) -> Optional[RuleDefinition]:
        """Get a rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            Rule definition or None if not found
        """
        return self.rules.get(rule_id)

    def list_all(self, enabled_only: bool = False) -> list[RuleDefinition]:
        """List all rules.

        Args:
            enabled_only: If True, only return enabled rules

        Returns:
            List of rules sorted by priority (descending)
        """
        rules = list(self.rules.values())

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        # Sort by priority (higher first)
        rules.sort(key=lambda r: r.priority, reverse=True)
        return rules

    def update(self, rule_id: str, rule: RuleDefinition) -> RuleDefinition:
        """Update an existing rule.

        Args:
            rule_id: Rule ID to update
            rule: New rule definition

        Returns:
            Updated rule

        Raises:
            ValueError: If rule not found or ID mismatch
        """
        if rule_id not in self.rules:
            raise ValueError(f"Rule with ID {rule_id} not found")

        if rule.rule_id != rule_id:
            raise ValueError(f"Rule ID mismatch: {rule.rule_id} != {rule_id}")

        self.rules[rule_id] = rule
        self._save_to_file()
        return rule

    def delete(self, rule_id: str) -> bool:
        """Delete a rule.

        Args:
            rule_id: Rule ID to delete

        Returns:
            True if deleted, False if not found
        """
        if rule_id not in self.rules:
            return False

        del self.rules[rule_id]
        self._save_to_file()
        return True

    def clear(self):
        """Clear all rules (for testing)."""
        self.rules.clear()
        if self.rules_file and self.rules_file.exists():
            self.rules_file.unlink()


# Global rule store instance
_rule_store: Optional[RuleStore] = None


def get_rule_store(rules_file: Optional[str] = None) -> RuleStore:
    """Get or create global rule store instance.

    Args:
        rules_file: Path to rules file (only used on first call)

    Returns:
        RuleStore instance
    """
    global _rule_store
    if _rule_store is None:
        _rule_store = RuleStore(rules_file=rules_file)
    return _rule_store
