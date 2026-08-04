"""MASKAI — Transaction repository with idempotency (CR-009)"""
import json, logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from maskai.clients.supabase import supabase_get, supabase_post

log = logging.getLogger("maskai.repo.transaction")


class CreateTransactionStatus(str, Enum):
    CREATED = "created"
    ALREADY_EXISTS = "already_exists"
    FAILED = "failed"


@dataclass(frozen=True)
class CreateTransactionResult:
    status: CreateTransactionStatus
    transaction: Optional[dict[str, Any]] = None
    error: Optional[str] = None


def is_unique_violation(result) -> bool:
    """Detect PostgreSQL unique violation (SQLSTATE 23505)"""
    if not result:
        return False
    data = result.data if hasattr(result, 'data') else result
    if isinstance(data, dict):
        return str(data.get("code", "")) == "23505"
    return False


def create_transaction(*, user_id: int, update_id: Optional[int],
                       payload: dict, source: str = "unknown") -> CreateTransactionResult:
    """Idempotent transaction insert — database as arbiter.

    Returns CREATED, ALREADY_EXISTS, or FAILED.
    Handles SQLSTATE 23505 as successful no-op.
    """
    full_payload = dict(payload)
    if update_id is not None:
        metadata = dict(full_payload.get("metadata") or {})
        metadata.update({
            "telegram_update_id": str(update_id),
            "source": source,
        })
        full_payload["metadata"] = metadata
        full_payload["telegram_update_id"] = update_id  # typed column for unique index

    result = supabase_post("maskai_transactions", full_payload)

    if result.ok:
        return CreateTransactionResult(
            status=CreateTransactionStatus.CREATED,
            transaction=result.data if isinstance(result.data, dict) else None,
        )

    if is_unique_violation(result):
        log.info(
            "Duplicate Telegram update — treating as successful no-op",
            extra={"update_id": update_id, "user_id": user_id},
        )
        # Try to fetch the existing row
        existing = None
        if update_id is not None:
            r = supabase_get("maskai_transactions", {
                "user_id": f"eq.{user_id}",
                "metadata->>telegram_update_id": f"eq.{update_id}",
                "select": "id,type,amount,description,transaction_dt,category_id,metadata",
                "limit": "1",
            })
            rows = r.data if r.ok and isinstance(r.data, list) else []
            existing = rows[0] if rows else None

        return CreateTransactionResult(
            status=CreateTransactionStatus.ALREADY_EXISTS,
            transaction=existing,
        )

    log.error(
        "Transaction insert failed",
        extra={"update_id": update_id, "user_id": user_id, "source": source,
               "status": getattr(result, 'status', 0)},
    )
    return CreateTransactionResult(
        status=CreateTransactionStatus.FAILED,
        error=getattr(result, 'error', 'Unknown error'),
    )
