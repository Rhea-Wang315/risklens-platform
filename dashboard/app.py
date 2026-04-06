from __future__ import annotations

import json
import os
from typing import Any

import httpx
import streamlit as st

DEFAULT_API_BASE_URL = os.getenv("RISKLENS_API_BASE_URL", "http://localhost:8000")


def _demo_alert_payload(i: int) -> dict[str, Any]:
    pattern_types = [
        "WASH_TRADING",
        "SANDWICH_ATTACK",
        "VOLUME_INFLATION",
        "BURST_TRADING",
        "ROUNDTRIP",
        "UNKNOWN",
    ]
    score = round(0.2 + (i % 20) * 0.04, 2)
    return {
        "alert_id": f"demo_alert_{i:04d}",
        "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "chain": "ethereum",
        "pool": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
        "pair": "WETH/USDC",
        "time_window_sec": 300,
        "pattern_type": pattern_types[i % len(pattern_types)],
        "score": score,
        "features": {
            "counterparty_diversity": 2,
            "roundtrip_count": 15,
            "total_volume_usd": 125000,
            "avg_time_between_trades_sec": 18,
        },
        "evidence_samples": [
            {
                "tx_hash": "0xabc123...",
                "timestamp": "2026-02-25T10:30:00Z",
                "action": "swap",
                "amount_usd": 5000,
            }
        ],
        "detected_at": "2026-02-25T10:35:00Z",
    }


def _safe_json_object(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if not raw:
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def _safe_json_object_list(raw: str) -> list[dict[str, Any]]:
    raw = raw.strip()
    if not raw:
        return []
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("Expected a JSON list")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i} must be a JSON object")
        out.append(item)
    return out


def _client() -> httpx.Client:
    return httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0))


def _api_get(base_url: str, path: str, params: dict[str, Any] | None = None) -> Any:
    with _client() as client:
        resp = client.get(f"{base_url}{path}", params=params)
        resp.raise_for_status()
        return resp.json()


def _api_post(base_url: str, path: str, payload: dict[str, Any]) -> Any:
    with _client() as client:
        resp = client.post(f"{base_url}{path}", json=payload)
        resp.raise_for_status()
        return resp.json()


def _api_put(base_url: str, path: str, payload: dict[str, Any]) -> Any:
    with _client() as client:
        resp = client.put(f"{base_url}{path}", json=payload)
        resp.raise_for_status()
        return resp.json()


def _api_patch(base_url: str, path: str, payload: dict[str, Any]) -> Any:
    with _client() as client:
        resp = client.patch(f"{base_url}{path}", json=payload)
        resp.raise_for_status()
        return resp.json()


def _api_delete(base_url: str, path: str) -> None:
    with _client() as client:
        resp = client.delete(f"{base_url}{path}")
        resp.raise_for_status()


def _render_health(base_url: str) -> None:
    st.subheader("API Health")
    try:
        health = _api_get(base_url, "/health")
        st.success("API reachable")
        st.json(health)
    except Exception as e:
        st.error("API not reachable")
        st.caption(str(e))


def _page_recent_decisions(base_url: str) -> None:
    st.header("Recent Decisions")

    with st.sidebar:
        st.subheader("Decisions Filter")
        address = st.text_input("Address", value="")
        risk_level = st.selectbox("Risk Level", options=["", "LOW", "MEDIUM", "HIGH", "CRITICAL"])
        action = st.selectbox("Action", options=["", "OBSERVE", "WARN", "FREEZE", "ESCALATE"])
        limit = st.number_input("Limit", min_value=1, max_value=1000, value=100, step=10)
        offset = st.number_input("Offset", min_value=0, value=0, step=10)
        refresh = st.button("Refresh")

    params: dict[str, Any] = {"limit": int(limit), "offset": int(offset)}
    if address.strip():
        params["address"] = address.strip()
    if risk_level:
        params["risk_level"] = risk_level
    if action:
        params["action"] = action

    if refresh:
        st.cache_data.clear()

    @st.cache_data(ttl=2)
    def _fetch_decisions(_base_url: str, _params: dict[str, Any]) -> list[dict[str, Any]]:
        data = _api_get(_base_url, "/api/v1/decisions", params=_params)
        if not isinstance(data, list):
            raise ValueError("/api/v1/decisions must return a list")
        return data

    try:
        decisions = _fetch_decisions(base_url, params)
        st.caption(f"Returned {len(decisions)} decisions")
        if decisions:
            st.dataframe(decisions, use_container_width=True)
        else:
            st.info("No decisions yet. Use 'Evaluate Alert' to generate one.")
    except Exception as e:
        st.error("Failed to load decisions")
        st.caption(str(e))


def _page_evaluate_alert(base_url: str) -> None:
    st.header("Evaluate Alert")

    left, right = st.columns([2, 1])

    with left:
        address = st.text_input("Address", value="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
        chain = st.text_input("Chain", value="ethereum")
        pool = st.text_input("Pool (optional)", value="")
        pair = st.text_input("Pair (optional)", value="WETH/USDC")
        time_window_sec = st.number_input("Time Window (sec)", min_value=1, value=300, step=30)
        pattern_type = st.selectbox(
            "Pattern Type",
            options=[
                "WASH_TRADING",
                "SANDWICH_ATTACK",
                "VOLUME_INFLATION",
                "BURST_TRADING",
                "ROUNDTRIP",
                "UNKNOWN",
            ],
            index=0,
        )
        score = st.slider("Detection Score", min_value=0.0, max_value=1.0, value=0.87, step=0.01)

        features_raw = st.text_area(
            "Features JSON (optional)",
            value=json.dumps(
                {
                    "counterparty_diversity": 2,
                    "roundtrip_count": 15,
                    "total_volume_usd": 125000,
                    "avg_time_between_trades_sec": 18,
                },
                indent=2,
            ),
            height=160,
        )
        samples_raw = st.text_area(
            "Evidence Samples JSON list (optional)",
            value=json.dumps(
                [
                    {
                        "tx_hash": "0xabc123...",
                        "timestamp": "2026-02-25T10:30:00Z",
                        "action": "swap",
                        "amount_usd": 5000,
                    }
                ],
                indent=2,
            ),
            height=140,
        )
        submit = st.button("Evaluate", type="primary")

    with right:
        st.subheader("Demo Tips")
        st.write("- Create/update rules on the Rules page")
        st.write("- Re-run evaluation to show changes")
        st.write("- Kafka can be down; API still works")

    if not submit:
        return

    try:
        features = _safe_json_object(features_raw)
        samples = _safe_json_object_list(samples_raw)

        payload: dict[str, Any] = {
            "address": address.strip(),
            "chain": chain.strip(),
            "pool": pool.strip() or None,
            "pair": pair.strip() or None,
            "time_window_sec": int(time_window_sec),
            "pattern_type": pattern_type,
            "score": float(score),
            "features": features,
            "evidence_samples": samples,
        }

        decision = _api_post(base_url, "/api/v1/evaluate", payload)
        st.success("Decision generated")

        c1, c2, c3 = st.columns(3)
        c1.metric("Risk Level", str(decision.get("risk_level", "")))
        c2.metric("Action", str(decision.get("action", "")))
        c3.metric("Risk Score", str(decision.get("risk_score", "")))

        st.subheader("Rationale")
        st.write(decision.get("rationale", ""))

        st.subheader("Full Response")
        st.json(decision)

    except httpx.HTTPStatusError as e:
        st.error("API returned an error")
        try:
            st.json(e.response.json())
        except Exception:
            st.text(e.response.text)
    except Exception as e:
        st.error("Failed to evaluate alert")
        st.caption(str(e))


def _page_rules(base_url: str) -> None:
    st.header("Rules Management")
    st.caption("Change rules at runtime; no redeploy needed")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        try:
            rules = _api_get(base_url, "/api/v1/rules")
            if not isinstance(rules, list):
                raise ValueError("/api/v1/rules must return a list")
        except Exception as e:
            st.error("Failed to load rules")
            st.caption(str(e))
            return

        st.subheader("Current Rules")
        if rules:
            st.dataframe(rules, use_container_width=True)
        else:
            st.info("No rules yet. Create one on the right.")

    with col_right:
        st.subheader("Create Rule")
        with st.form("create_rule"):
            rule_id = st.text_input("rule_id (optional)", value="")
            name = st.text_input("name", value="High Risk Freeze")
            description = st.text_input("description", value="Freeze accounts with score >= 0.9")
            pattern_types = st.multiselect(
                "pattern_types",
                options=[
                    "SANDWICH_ATTACK",
                    "WASH_TRADING",
                    "VOLUME_INFLATION",
                    "BURST_TRADING",
                    "ROUNDTRIP",
                    "UNKNOWN",
                ],
                default=["WASH_TRADING"],
            )
            action = st.selectbox(
                "action", options=["OBSERVE", "WARN", "FREEZE", "ESCALATE"], index=2
            )
            priority = st.number_input("priority", value=100, step=10)
            enabled = st.checkbox("enabled", value=True)
            conditions_raw = st.text_area(
                "conditions JSON",
                value=json.dumps({"score": {"gte": 0.9}}, indent=2),
                height=120,
            )
            submitted = st.form_submit_button("Create", type="primary")

        if submitted:
            try:
                conditions = _safe_json_object(conditions_raw)
                payload: dict[str, Any] = {
                    "name": name,
                    "description": description,
                    "pattern_types": pattern_types,
                    "conditions": conditions,
                    "action": action,
                    "priority": int(priority),
                    "enabled": bool(enabled),
                }
                if rule_id.strip():
                    payload["rule_id"] = rule_id.strip()

                created = _api_post(base_url, "/api/v1/rules", payload)
                st.success(f"Created rule: {created.get('rule_id', '')}")
                st.cache_data.clear()
            except Exception as e:
                st.error("Failed to create rule")
                st.caption(str(e))

        st.divider()
        st.subheader("Edit / Delete Rule")

        rule_ids = [r.get("rule_id", "") for r in rules if isinstance(r, dict) and r.get("rule_id")]
        selected_rule_id = st.selectbox("Select rule_id", options=[""] + sorted(rule_ids))
        if not selected_rule_id:
            return

        try:
            selected_rule = _api_get(base_url, f"/api/v1/rules/{selected_rule_id}")
            if not isinstance(selected_rule, dict):
                raise ValueError("Rule response must be a JSON object")
        except Exception as e:
            st.error("Failed to load selected rule")
            st.caption(str(e))
            return

        edited_raw = st.text_area(
            "Rule JSON (edit then Save)",
            value=json.dumps(selected_rule, indent=2),
            height=260,
        )

        c_save, c_delete = st.columns(2)
        save = c_save.button("Save (PUT)")
        delete = c_delete.button("Delete")

        if save:
            try:
                payload = json.loads(edited_raw)
                if not isinstance(payload, dict):
                    raise ValueError("Rule JSON must be an object")
                if payload.get("rule_id") != selected_rule_id:
                    raise ValueError("rule_id must match the selected rule_id")
                updated = _api_put(base_url, f"/api/v1/rules/{selected_rule_id}", payload)
                st.success(f"Updated rule: {updated.get('rule_id', '')}")
                st.cache_data.clear()
            except Exception as e:
                st.error("Failed to update rule")
                st.caption(str(e))

        if delete:
            try:
                _api_delete(base_url, f"/api/v1/rules/{selected_rule_id}")
                st.success("Deleted")
                st.cache_data.clear()
            except Exception as e:
                st.error("Failed to delete rule")
                st.caption(str(e))


def _page_address_profile(base_url: str) -> None:
    st.header("Address Profile")
    st.caption("Quick risk profile for one address based on decision history")

    with st.sidebar:
        st.subheader("Address Profile")
        address = st.text_input(
            "Address to Profile", value="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        )
        recent_limit = st.number_input(
            "Recent decisions", min_value=1, max_value=200, value=20, step=5
        )
        load_profile = st.button("Load Profile")

    if not load_profile and "address_profile_data" not in st.session_state:
        st.info("Enter an address and click 'Load Profile'.")
        return

    if load_profile:
        try:
            path = f"/api/v1/addresses/{address.strip()}/profile"
            profile = _api_get(base_url, path, params={"recent_limit": int(recent_limit)})
            if not isinstance(profile, dict):
                raise ValueError("Profile response must be a JSON object")
            st.session_state["address_profile_data"] = profile
            st.session_state["address_profile_address"] = address.strip()
        except httpx.HTTPStatusError as e:
            st.error("API returned an error")
            try:
                st.json(e.response.json())
            except Exception:
                st.text(e.response.text)
            return
        except Exception as e:
            st.error("Failed to load address profile")
            st.caption(str(e))
            return

    profile = st.session_state.get("address_profile_data")
    if not isinstance(profile, dict):
        st.info("No profile loaded yet.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Decisions", str(profile.get("total_decisions", 0)))
    c2.metric("Avg Risk Score", str(profile.get("avg_risk_score", 0)))
    c3.metric("Most Recent", str(profile.get("latest_decided_at", "N/A")))

    st.subheader("Action Distribution")
    st.json(profile.get("action_counts", {}))

    st.subheader("Risk Level Distribution")
    st.json(profile.get("risk_level_counts", {}))

    st.subheader("Pattern Type Distribution")
    st.json(profile.get("pattern_type_counts", {}))

    st.subheader("Recent Decisions")
    recent_decisions = profile.get("recent_decisions", [])
    if isinstance(recent_decisions, list) and recent_decisions:
        st.dataframe(recent_decisions, use_container_width=True)
    else:
        st.info("No recent decisions available.")


def _page_triage(base_url: str) -> None:
    st.header("Triage Queue")
    st.caption("Review open decisions, assign owners, and update triage status")

    with st.sidebar:
        st.subheader("Triage Filters")
        status = st.selectbox(
            "Status",
            options=["", "OPEN", "IN_REVIEW", "RESOLVED", "FALSE_POSITIVE"],
        )
        assignee = st.text_input("Assignee", value="")
        limit = st.number_input("Limit", min_value=1, max_value=500, value=50, step=10)
        refresh = st.button("Refresh Triage")

    params: dict[str, Any] = {"limit": int(limit), "offset": 0}
    if status:
        params["decision_status"] = status
    if assignee.strip():
        params["triage_assignee"] = assignee.strip()

    if refresh:
        st.cache_data.clear()

    @st.cache_data(ttl=2)
    def _fetch_triage_items(_base_url: str, _params: dict[str, Any]) -> list[dict[str, Any]]:
        data = _api_get(_base_url, "/api/v1/decisions", params=_params)
        if not isinstance(data, list):
            raise ValueError("/api/v1/decisions must return a list")
        return data

    try:
        decisions = _fetch_triage_items(base_url, params)
    except Exception as e:
        st.error("Failed to load triage queue")
        st.caption(str(e))
        return

    st.caption(f"Returned {len(decisions)} decisions")
    if not decisions:
        st.info("No decisions found for current filters.")
        return

    st.dataframe(decisions, use_container_width=True)

    decision_options = [d.get("decision_id", "") for d in decisions if isinstance(d, dict)]
    selected_decision_id = st.selectbox("Select decision_id", options=decision_options)
    selected = next((d for d in decisions if d.get("decision_id") == selected_decision_id), None)
    if not isinstance(selected, dict):
        return

    default_status = str(selected.get("decision_status", "OPEN"))
    status_options = ["OPEN", "IN_REVIEW", "RESOLVED", "FALSE_POSITIVE"]
    default_idx = status_options.index(default_status) if default_status in status_options else 0

    with st.form("triage_update_form"):
        new_status = st.selectbox("New Status", options=status_options, index=default_idx)
        new_assignee = st.text_input("Assignee", value=str(selected.get("triage_assignee") or ""))
        new_notes = st.text_area("Notes", value=str(selected.get("triage_notes") or ""), height=120)
        submitted = st.form_submit_button("Update Triage", type="primary")

    if not submitted:
        return

    try:
        updated = _api_patch(
            base_url,
            f"/api/v1/decisions/{selected_decision_id}/triage",
            payload={
                "decision_status": new_status,
                "triage_assignee": new_assignee.strip() or None,
                "triage_notes": new_notes.strip() or None,
            },
        )
        st.success("Triage updated")
        st.json(updated)
        st.cache_data.clear()
    except httpx.HTTPStatusError as e:
        st.error("API returned an error")
        try:
            st.json(e.response.json())
        except Exception:
            st.text(e.response.text)
    except Exception as e:
        st.error("Failed to update triage")
        st.caption(str(e))


def main() -> None:
    st.set_page_config(page_title="RiskLens Dashboard", layout="wide")
    st.title("RiskLens Operator Dashboard")
    st.caption("Week 3 demo UI: decisions, evaluation, and rule management")

    with st.sidebar:
        st.subheader("Connection")
        base_url = st.text_input("API Base URL", value=DEFAULT_API_BASE_URL)
        st.caption("Tip: set RISKLENS_API_BASE_URL to avoid retyping")
        st.divider()
        st.subheader("Demo")
        demo_count = st.number_input(
            "Generate decisions", min_value=1, max_value=200, value=25, step=5
        )
        demo_generate = st.button("Generate Demo Data")
        st.divider()
        page = st.radio(
            "Page",
            options=["Recent Decisions", "Evaluate Alert", "Rules", "Address Profile", "Triage"],
            index=0,
        )

    if demo_generate:
        try:
            for i in range(int(demo_count)):
                _api_post(base_url, "/api/v1/evaluate", _demo_alert_payload(i))
            st.success(f"Generated {int(demo_count)} decisions")
            st.cache_data.clear()
        except Exception as e:
            st.error("Failed to generate demo data")
            st.caption(str(e))

    _render_health(base_url)
    st.divider()

    if page == "Recent Decisions":
        _page_recent_decisions(base_url)
    elif page == "Evaluate Alert":
        _page_evaluate_alert(base_url)
    elif page == "Rules":
        _page_rules(base_url)
    elif page == "Address Profile":
        _page_address_profile(base_url)
    else:
        _page_triage(base_url)


if __name__ == "__main__":
    main()
