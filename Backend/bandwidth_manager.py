"""
Activity-aware bandwidth management utilities.

This module provides:
1) User activity aggregation from detections
2) Activity + ML based bandwidth recommendations
3) Effective bandwidth policy resolution (manual/preset/auto)
4) Linux tc shaping helpers for active client sessions
"""

from __future__ import annotations

import logging
import ipaddress
import os
import subprocess
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from db import db, sessions_collection, users_collection

try:
    from Detection_Management.bandwidth_ml_model import (
        auto_assign_bandwidth as ml_auto_assign_bandwidth,
    )
except Exception:
    ml_auto_assign_bandwidth = None


logger = logging.getLogger(__name__)

detections_collection = db["detections"]

MIN_CUSTOM_MBPS = 1
MAX_CUSTOM_MBPS = 500
DEFAULT_MANUAL_MBPS = 50


def _env_tier_mbps(env_key: str, default_value: int) -> int:
    raw_value = os.environ.get(env_key)
    try:
        parsed = int(float(raw_value)) if raw_value is not None else int(default_value)
    except (TypeError, ValueError):
        parsed = int(default_value)
    return max(MIN_CUSTOM_MBPS, min(MAX_CUSTOM_MBPS, parsed))

TIER_TO_MBPS: Dict[str, int] = {
    "low": _env_tier_mbps("BANDWIDTH_TIER_LOW_MBPS", 2),
    "medium": _env_tier_mbps("BANDWIDTH_TIER_MEDIUM_MBPS", 5),
    "high": _env_tier_mbps("BANDWIDTH_TIER_HIGH_MBPS", 20),
}

TIER_ORDER: Dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
}

CATEGORY_LABELS: Dict[str, str] = {
    "gaming": "Gaming",
    "video": "YouTube/Video",
    "streaming": "Streaming",
    "social": "Social Media",
    "messaging": "Messaging",
    "search": "Research/Browsing",
    "system": "System/Background",
    "general": "General Browsing",
}

DEFAULT_TIER = "medium"

_bandwidth_daemon_thread: Optional[threading.Thread] = None


def get_bandwidth_presets() -> Dict[str, int]:
    return dict(TIER_TO_MBPS)


def _extract_route_device(route_output: str) -> Optional[str]:
    for line in (route_output or "").splitlines():
        parts = line.split()
        if "dev" not in parts:
            continue
        idx = parts.index("dev")
        if idx + 1 < len(parts):
            return parts[idx + 1].strip()
    return None


def _detect_hotspot_interface_from_system() -> Optional[str]:
    hotspot_subnet = os.environ.get("HOTSPOT_SUBNET", "192.168.50.0/24")
    hotspot_gateway_ip = os.environ.get("HOTSPOT_GATEWAY_IP", "192.168.50.1")
    octets = str(hotspot_gateway_ip).split(".")
    hotspot_prefix = ".".join(octets[:3]) + "." if len(octets) == 4 else "192.168.50."

    try:
        route_result = subprocess.run(
            ["ip", "-4", "route", "show", hotspot_subnet],
            capture_output=True,
            text=True,
            check=False,
        )
        route_device = _extract_route_device(route_result.stdout)
        if route_device:
            return route_device
    except Exception:
        pass

    try:
        addr_result = subprocess.run(
            ["ip", "-o", "-4", "addr", "show"],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in (addr_result.stdout or "").splitlines():
            parts = line.split()
            if len(parts) < 4 or parts[2] != "inet":
                continue
            iface = parts[1].strip()
            ip_addr = parts[3].split("/", 1)[0].strip()
            if ip_addr.startswith(hotspot_prefix):
                return iface
    except Exception:
        pass

    return None


def _get_hotspot_interface() -> str:
    """Resolve hotspot interface from firewall manager or fallback env/default."""
    configured_interface = (os.environ.get("HOTSPOT_INTERFACE") or "").strip()
    if configured_interface:
        return configured_interface

    detected_interface = _detect_hotspot_interface_from_system()
    if detected_interface:
        return detected_interface

    try:
        from linux_firewall_manager import get_firewall_manager

        manager = get_firewall_manager()
        if manager and getattr(manager, "hotspot_interface", None):
            return manager.hotspot_interface
    except Exception:
        pass

    return "wlx782051ac644f"


def _normalize_tier(value: Any, default: str = DEFAULT_TIER) -> str:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in TIER_TO_MBPS:
            return lowered
    return default


def _clamp_custom_mbps(value: Any, default: int = DEFAULT_MANUAL_MBPS) -> int:
    try:
        numeric = int(float(value))
    except (TypeError, ValueError):
        numeric = default
    return max(MIN_CUSTOM_MBPS, min(MAX_CUSTOM_MBPS, numeric))


def _get_hotspot_network() -> Any:
    subnet = os.environ.get("HOTSPOT_SUBNET", "192.168.50.0/24")
    try:
        return ipaddress.ip_network(subnet, strict=False)
    except Exception:
        return ipaddress.ip_network("192.168.50.0/24", strict=False)


def get_user_activity_snapshot(roll_no: str, window_minutes: int = 120) -> Dict[str, Any]:
    """Summarize user activity in a recent time window."""
    since = datetime.utcnow() - timedelta(minutes=window_minutes)

    category_pipeline = [
        {"$match": {"roll_no": str(roll_no), "timestamp": {"$gte": since}}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]

    app_pipeline = [
        {"$match": {"roll_no": str(roll_no), "timestamp": {"$gte": since}}},
        {"$group": {"_id": "$app_name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1},
    ]

    category_stats = list(detections_collection.aggregate(category_pipeline))
    top_app_stats = list(detections_collection.aggregate(app_pipeline))

    total = int(sum(int(item.get("count", 0)) for item in category_stats))
    dominant_category = "general"
    dominant_count = 0
    if category_stats:
        dominant_category = str(category_stats[0].get("_id") or "general").lower()
        dominant_count = int(category_stats[0].get("count", 0))

    dominant_share = (dominant_count / total) if total else 0.0

    top_app = "Unknown"
    if top_app_stats:
        top_app = str(top_app_stats[0].get("_id") or "Unknown")

    latest_detection = detections_collection.find_one(
        {"roll_no": str(roll_no)},
        sort=[("timestamp", -1)],
        projection={"domain": 1, "app_name": 1, "timestamp": 1},
    )

    latest_domain = (latest_detection or {}).get("domain", "")
    label = CATEGORY_LABELS.get(dominant_category, "General Browsing")

    if top_app and top_app != "Unknown":
        detected_activity = f"{label} ({top_app})"
    else:
        detected_activity = label

    return {
        "roll_no": str(roll_no),
        "window_minutes": int(window_minutes),
        "total_requests": total,
        "dominant_category": dominant_category,
        "dominant_count": dominant_count,
        "dominant_share": round(dominant_share, 4),
        "category_counts": {
            str(item.get("_id") or "general").lower(): int(item.get("count", 0))
            for item in category_stats
        },
        "top_app": top_app,
        "latest_domain": latest_domain,
        "detected_activity": detected_activity,
    }


def _rule_based_tier(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Compute rule-based recommendation from activity snapshot."""
    total = int(snapshot.get("total_requests") or 0)
    dominant = str(snapshot.get("dominant_category") or "general").lower()
    dominant_share = float(snapshot.get("dominant_share") or 0.0)

    if total == 0:
        return {
            "tier": "low",
            "confidence": 0.55,
            "reason": "No recent activity detected; assigning conservative baseline.",
        }

    if dominant in ("gaming", "video", "streaming"):
        tier = "high"
        reason = "High-bandwidth activity detected (gaming/streaming/video)."
    elif dominant in ("social", "general"):
        tier = "medium"
        reason = "Mixed browsing/social usage detected."
    elif dominant in ("search", "messaging", "system"):
        if total < 80:
            tier = "low"
            reason = "Light research/messaging/system usage detected."
        else:
            tier = "medium"
            reason = "Sustained non-media usage detected."
    else:
        tier = "medium"
        reason = "Balanced usage detected."

    # Escalate heavy overall activity by one tier where reasonable
    if total > 220 and tier != "high":
        tier = "high" if tier == "medium" else "medium"
        reason += " Overall request volume is high."

    confidence = min(0.95, 0.55 + (dominant_share * 0.4))
    return {
        "tier": tier,
        "confidence": round(confidence, 4),
        "reason": reason,
    }


def recommend_bandwidth_for_roll_no(roll_no: str, window_minutes: int = 120) -> Dict[str, Any]:
    """
    Recommend user bandwidth based on activity + optional ML model output.
    Returns tier, confidence, explanation, and activity features.
    """
    try:
        snapshot = get_user_activity_snapshot(roll_no, window_minutes=window_minutes)
    except Exception as error:
        logger.warning("Activity snapshot unavailable for %s: %s", roll_no, error)
        snapshot = {
            "roll_no": str(roll_no),
            "window_minutes": int(window_minutes),
            "total_requests": 0,
            "dominant_category": "general",
            "dominant_count": 0,
            "dominant_share": 0.0,
            "category_counts": {},
            "top_app": "Unknown",
            "latest_domain": "",
            "detected_activity": "General Browsing",
        }

    rules = _rule_based_tier(snapshot)

    selected_tier = rules["tier"]
    confidence = float(rules["confidence"])
    explanation_parts = [rules["reason"]]

    ml_tier = None
    ml_confidence = None

    if ml_auto_assign_bandwidth is not None:
        try:
            ml_result = ml_auto_assign_bandwidth(str(roll_no))
            ml_tier = _normalize_tier(ml_result.get("tier"), default=selected_tier)
            ml_confidence = float(ml_result.get("confidence", 0.0))

            dominant = snapshot.get("dominant_category", "general")
            dominant_share = float(snapshot.get("dominant_share", 0.0))

            # Rule priority for clearly heavy categories
            if dominant in ("gaming", "video", "streaming") and dominant_share >= 0.2:
                selected_tier = "high"
                confidence = max(confidence, ml_confidence)
                explanation_parts.append(
                    "Dominant high-throughput activity confirmed; prioritizing HIGH tier."
                )
            else:
                # Blend rule + ML outputs
                if TIER_ORDER.get(ml_tier, 1) > TIER_ORDER.get(selected_tier, 1):
                    selected_tier = ml_tier
                confidence = (confidence * 0.45) + (ml_confidence * 0.55)
                explanation_parts.append(
                    f"ML model suggests {ml_tier.upper()} tier ({ml_confidence:.0%} confidence)."
                )

        except Exception as error:
            logger.warning("Bandwidth ML recommendation failed for %s: %s", roll_no, error)
            explanation_parts.append("ML recommendation unavailable; using activity rules.")

    confidence = max(0.0, min(1.0, confidence))
    selected_tier = _normalize_tier(selected_tier)

    return {
        "roll_no": str(roll_no),
        "tier": selected_tier,
        "confidence": round(confidence, 4),
        "recommended_mbps": TIER_TO_MBPS[selected_tier],
        "detected_activity": snapshot.get("detected_activity", "General Browsing"),
        "dominant_category": snapshot.get("dominant_category", "general"),
        "dominant_share": snapshot.get("dominant_share", 0.0),
        "total_requests": snapshot.get("total_requests", 0),
        "top_app": snapshot.get("top_app", "Unknown"),
        "window_minutes": window_minutes,
        "ml_tier": ml_tier,
        "ml_confidence": ml_confidence,
        "explanation": " ".join(part for part in explanation_parts if part).strip(),
    }


def resolve_effective_bandwidth(user_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve effective bandwidth policy from user document settings."""
    raw_limit = user_doc.get("bandwidth_limit", DEFAULT_TIER)

    # Numeric bandwidth_limit is treated as manual Mbps
    if isinstance(raw_limit, (int, float)):
        effective_mbps = _clamp_custom_mbps(raw_limit)
        return {
            "mode": "manual",
            "tier": "custom",
            "effective_mbps": effective_mbps,
        }

    mode = str(raw_limit).strip().lower() if isinstance(raw_limit, str) else DEFAULT_TIER

    if mode == "manual":
        effective_mbps = _clamp_custom_mbps(user_doc.get("bandwidth_custom_value"))
        return {
            "mode": "manual",
            "tier": "custom",
            "effective_mbps": effective_mbps,
        }

    if mode == "auto":
        auto_tier = _normalize_tier(user_doc.get("bandwidth_auto_assigned"), default=DEFAULT_TIER)
        return {
            "mode": "auto",
            "tier": auto_tier,
            "effective_mbps": TIER_TO_MBPS[auto_tier],
        }

    preset = _normalize_tier(mode)
    return {
        "mode": "preset",
        "tier": preset,
        "effective_mbps": TIER_TO_MBPS[preset],
    }


def _tc_command(args: List[str]) -> subprocess.CompletedProcess:
    commands: List[List[str]] = [["tc"] + args]
    if os.geteuid() != 0:
        commands.append(["sudo", "-n", "tc"] + args)

    last_result: Optional[subprocess.CompletedProcess] = None

    for command in commands:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as error:
            result = subprocess.CompletedProcess(
                args=command,
                returncode=127,
                stdout="",
                stderr=str(error),
            )

        last_result = result
        if result.returncode == 0:
            return result

        stderr_text = (result.stderr or "").lower()
        needs_escalation = (
            "operation not permitted" in stderr_text
            or "permission denied" in stderr_text
            or "not found" in stderr_text
        )

        if command[0] == "tc" and needs_escalation and len(commands) > 1:
            continue

        return result

    return last_result or subprocess.CompletedProcess(
        args=["tc"] + args,
        returncode=1,
        stdout="",
        stderr="tc command failed",
    )


def _tc_error_message(result: subprocess.CompletedProcess) -> str:
    message = (result.stderr or "").strip() or (result.stdout or "").strip()
    lowered = message.lower()
    if "sudo: a password is required" in lowered:
        return "Permission denied for tc. Run backend as root/sudo or configure passwordless sudo for tc commands."
    if "operation not permitted" in lowered or "permission denied" in lowered:
        return "Insufficient NET_ADMIN privileges for tc. Start backend with root privileges."
    if message:
        return message
    return f"tc command failed with exit code {result.returncode}"


def _classid_for_policy_index(index: int) -> str:
    # Keep class ids in safe range while avoiding collisions in normal operation.
    class_num = 1000 + (index % 54000)
    return f"1:{class_num}"


def _qdisc_handle_for_policy_index(index: int) -> str:
    handle_num = 2000 + (index % 54000)
    return f"{handle_num}:"


def _priority_for_tier(tier: str) -> int:
    normalized = _normalize_tier(tier)
    if normalized == "high":
        return 1
    if normalized == "medium":
        return 2
    return 3


def _ensure_qos_base(interface: str) -> Dict[str, Any]:
    """Create/refresh root HTB classes for per-client shaping."""
    root_rate_mbps = _clamp_custom_mbps(
        os.environ.get("BANDWIDTH_ROOT_RATE_MBPS", "300"),
        default=300,
    )

    # Reset root qdisc to avoid stale/incompatible qdisc state.
    # Some kernels/drivers fail with "change operation not supported" when using replace.
    _tc_command(["qdisc", "del", "dev", interface, "root"])
    _tc_command(["qdisc", "del", "dev", interface, "ingress"])

    commands = [
        ["qdisc", "add", "dev", interface, "root", "handle", "1:", "htb", "default", "999"],
        [
            "class",
            "add",
            "dev",
            interface,
            "parent",
            "1:",
            "classid",
            "1:1",
            "htb",
            "rate",
            f"{root_rate_mbps}mbit",
            "ceil",
            f"{root_rate_mbps}mbit",
        ],
        ["class", "add", "dev", interface, "parent", "1:1", "classid", "1:999", "htb", "rate", "2mbit", "ceil", "5mbit", "prio", "7"],
        ["qdisc", "add", "dev", interface, "parent", "1:999", "handle", "1999:", "fq_codel"],
    ]

    for cmd in commands:
        result = _tc_command(cmd)
        if result.returncode != 0:
            message = _tc_error_message(result)
            logger.warning("tc setup failed (%s): %s", " ".join(cmd), message)
            return {"success": False, "message": message, "interface": interface}

    ingress_result = _tc_command(["qdisc", "add", "dev", interface, "handle", "ffff:", "ingress"])
    ingress_enabled = ingress_result.returncode == 0
    if not ingress_enabled:
        logger.warning("ingress qdisc setup failed on %s: %s", interface, _tc_error_message(ingress_result))

    return {
        "success": True,
        "interface": interface,
        "ingress_enabled": ingress_enabled,
    }


def apply_tc_bandwidth_policies(client_policies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply traffic shaping filters for active clients.

    Note: shaping is applied on hotspot egress (downloads to clients),
    matched by destination client IP.
    """
    interface = _get_hotspot_interface()

    setup_status = _ensure_qos_base(interface)
    if not setup_status.get("success"):
        return {
            "success": False,
            "interface": interface,
            "applied": 0,
            "failed": len(client_policies),
            "errors": [setup_status.get("message", "QoS base setup failed")],
        }

    # Remove existing filters then recreate from active sessions.
    _tc_command(["filter", "delete", "dev", interface, "parent", "1:"])
    ingress_enabled = bool(setup_status.get("ingress_enabled", False))
    if ingress_enabled:
        _tc_command(["filter", "delete", "dev", interface, "parent", "ffff:"])

    applied = 0
    errors: List[str] = []
    warnings: List[str] = []
    applied_policies: List[Dict[str, Any]] = []

    for index, policy in enumerate(client_policies, start=1):
        client_ip = str(policy.get("client_ip") or "").strip()
        if not client_ip:
            continue

        try:
            ipaddress.ip_address(client_ip)
        except ValueError:
            errors.append(f"{client_ip}: invalid client IP")
            continue

        effective_mbps = _clamp_custom_mbps(policy.get("effective_mbps"), default=TIER_TO_MBPS[DEFAULT_TIER])
        tier = str(policy.get("tier") or DEFAULT_TIER)
        classid = _classid_for_policy_index(index)
        qdisc_handle = _qdisc_handle_for_policy_index(index)
        filter_prio = 100 + index

        class_result = _tc_command(
            [
                "class",
                "add",
                "dev",
                interface,
                "parent",
                "1:1",
                "classid",
                classid,
                "htb",
                "rate",
                f"{effective_mbps}mbit",
                "ceil",
                f"{effective_mbps}mbit",
                "prio",
                str(_priority_for_tier(tier)),
            ]
        )

        if class_result.returncode != 0:
            errors.append(f"{client_ip}: {_tc_error_message(class_result)}")
            continue

        qdisc_result = _tc_command(
            [
                "qdisc",
                "add",
                "dev",
                interface,
                "parent",
                classid,
                "handle",
                qdisc_handle,
                "fq_codel",
            ]
        )

        if qdisc_result.returncode != 0:
            errors.append(f"{client_ip}: {_tc_error_message(qdisc_result)}")
            continue

        result = _tc_command(
            [
                "filter",
                "add",
                "dev",
                interface,
                "protocol",
                "ip",
                "parent",
                "1:",
                "prio",
                str(filter_prio),
                "u32",
                "match",
                "ip",
                "dst",
                f"{client_ip}/32",
                "flowid",
                classid,
            ]
        )

        if result.returncode == 0:
            applied += 1

            if ingress_enabled:
                ingress_filter_result = _tc_command(
                    [
                        "filter",
                        "add",
                        "dev",
                        interface,
                        "parent",
                        "ffff:",
                        "protocol",
                        "ip",
                        "prio",
                        str(filter_prio),
                        "u32",
                        "match",
                        "ip",
                        "src",
                        f"{client_ip}/32",
                        "police",
                        "rate",
                        f"{effective_mbps}mbit",
                        "burst",
                        "64k",
                        "drop",
                        "flowid",
                        ":1",
                    ]
                )
                if ingress_filter_result.returncode != 0:
                    warnings.append(
                        f"{client_ip}: upload shaping not applied: {_tc_error_message(ingress_filter_result)}"
                    )

            applied_policies.append(
                {
                    "roll_no": str(policy.get("roll_no") or ""),
                    "client_ip": client_ip,
                    "effective_mbps": effective_mbps,
                    "tier": _normalize_tier(tier),
                    "classid": classid,
                }
            )
        else:
            message = _tc_error_message(result)
            errors.append(f"{client_ip}: {message}")

    return {
        "success": len(errors) == 0,
        "interface": interface,
        "applied": applied,
        "failed": len(errors),
        "errors": errors,
        "warnings": warnings,
        "policies": applied_policies,
        "ingress_enabled": ingress_enabled,
    }


def assign_auto_bandwidth(roll_no: str) -> Dict[str, Any]:
    """Compute and persist auto bandwidth recommendation for one user."""
    recommendation = recommend_bandwidth_for_roll_no(roll_no)
    users_collection.update_one(
        {"roll_no": str(roll_no)},
        {
            "$set": {
                "bandwidth_limit": "auto",
                "bandwidth_auto_assigned": recommendation["tier"],
                "bandwidth_auto_confidence": recommendation["confidence"],
                "bandwidth_last_updated": datetime.utcnow(),
                "detected_activity": recommendation["detected_activity"],
                "activity_category": recommendation["dominant_category"],
                "activity_window_minutes": recommendation["window_minutes"],
                "activity_total_requests": recommendation["total_requests"],
            }
        },
    )

    return recommendation


def apply_bandwidth_for_active_users() -> Dict[str, Any]:
    """Resolve bandwidth for active sessions and apply tc filters."""
    active_sessions = list(sessions_collection.find({"status": "active"}))
    policies: List[Dict[str, Any]] = []
    skipped_sessions: List[Dict[str, Any]] = []
    hotspot_network = _get_hotspot_network()

    for session in active_sessions:
        roll_no = str(session.get("roll_no") or "").strip()
        client_ip = str(session.get("client_ip") or "").strip()
        if not roll_no or not client_ip:
            skipped_sessions.append(
                {
                    "roll_no": roll_no,
                    "client_ip": client_ip,
                    "reason": "missing roll_no/client_ip",
                }
            )
            continue

        try:
            ip_value = ipaddress.ip_address(client_ip)
        except ValueError:
            skipped_sessions.append(
                {
                    "roll_no": roll_no,
                    "client_ip": client_ip,
                    "reason": "invalid ip",
                }
            )
            continue

        if ip_value not in hotspot_network:
            skipped_sessions.append(
                {
                    "roll_no": roll_no,
                    "client_ip": client_ip,
                    "reason": f"outside hotspot subnet {hotspot_network}",
                }
            )
            continue

        user_doc = users_collection.find_one({"roll_no": roll_no}) or {}
        resolved = resolve_effective_bandwidth(user_doc)
        policy = {
            "roll_no": roll_no,
            "client_ip": client_ip,
            **resolved,
        }
        policies.append(policy)

        users_collection.update_one(
            {"roll_no": roll_no},
            {
                "$set": {
                    "bandwidth_effective_mode": resolved["mode"],
                    "bandwidth_effective_tier": resolved["tier"],
                    "bandwidth_effective_mbps": resolved["effective_mbps"],
                    "bandwidth_last_applied": datetime.utcnow(),
                }
            },
        )

    if not policies:
        return {
            "total_active_sessions": len(active_sessions),
            "total_active_users": 0,
            "skipped_sessions": skipped_sessions,
            "tc": {
                "success": True,
                "interface": _get_hotspot_interface(),
                "applied": 0,
                "failed": 0,
                "errors": [],
                "policies": [],
                "message": "No active users to shape",
            },
        }

    tc_result = apply_tc_bandwidth_policies(policies)
    return {
        "total_active_sessions": len(active_sessions),
        "total_active_users": len(policies),
        "skipped_sessions": skipped_sessions,
        "tc": tc_result,
    }


def refresh_auto_bandwidth_profiles(confidence_threshold: float = 0.5) -> Dict[str, Any]:
    """Recompute auto-tier users and apply latest policies for active sessions."""
    auto_users = list(users_collection.find({"role": "student", "bandwidth_limit": "auto"}))
    updated = 0
    skipped = 0

    for user in auto_users:
        roll_no = str(user.get("roll_no") or "").strip()
        if not roll_no:
            continue

        recommendation = recommend_bandwidth_for_roll_no(roll_no)
        confidence = float(recommendation.get("confidence", 0.0))

        if confidence < confidence_threshold:
            skipped += 1
            continue

        users_collection.update_one(
            {"roll_no": roll_no},
            {
                "$set": {
                    "bandwidth_auto_assigned": recommendation["tier"],
                    "bandwidth_auto_confidence": recommendation["confidence"],
                    "bandwidth_last_updated": datetime.utcnow(),
                    "detected_activity": recommendation["detected_activity"],
                    "activity_category": recommendation["dominant_category"],
                    "activity_total_requests": recommendation["total_requests"],
                }
            },
        )
        updated += 1

    apply_status = apply_bandwidth_for_active_users()
    return {
        "auto_users": len(auto_users),
        "updated": updated,
        "skipped": skipped,
        "apply_status": apply_status,
    }


def start_auto_bandwidth_daemon(interval_seconds: int = 300) -> None:
    """Start a background daemon that keeps AUTO users in sync."""
    global _bandwidth_daemon_thread

    if _bandwidth_daemon_thread and _bandwidth_daemon_thread.is_alive():
        return

    def _worker() -> None:
        logger.info("Starting auto bandwidth daemon (interval=%ss)", interval_seconds)
        while True:
            try:
                refresh_auto_bandwidth_profiles()
            except Exception as error:
                logger.warning("Auto bandwidth daemon cycle failed: %s", error)
            time.sleep(max(30, int(interval_seconds)))

    _bandwidth_daemon_thread = threading.Thread(target=_worker, daemon=True)
    _bandwidth_daemon_thread.start()
