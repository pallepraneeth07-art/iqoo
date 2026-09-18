from typing import Dict, Any, Tuple

def evaluate_transaction_status(
    gateway_status: str,
    bank_status: str,
    merchant_status: str,
    is_duplicate: bool = False
) -> Tuple[str, str, str, str]:
    """
    Evaluates system statuses and returns:
    (final_status, failure_reason, recovery_status, reconciliation_status)
    """

    g_status = gateway_status.upper()
    b_status = bank_status.upper()
    m_status = merchant_status.upper()

    if is_duplicate:
        return (
            "DUPLICATE",
            "Duplicate transaction detected with identical UPI reference and customer parameters within short window.",
            "VERIFICATION_PENDING",
            "DUPLICATE"
        )

    # Case 1: All SUCCESS
    if g_status == "SUCCESS" and b_status in ["SUCCESS", "DEBITED"] and m_status in ["SUCCESS", "CREDITED"]:
        return (
            "SUCCESS",
            None,
            "NOT_REQUIRED",
            "MATCHED"
        )

    # Case 3: DEBITED BUT NOT CREDITED (Bank debited, Gateway timeout/failed or Merchant not credited)
    if b_status in ["DEBITED", "SUCCESS"] and (m_status in ["NOT_CREDITED", "FAILED", "MISSING"] or g_status in ["TIMEOUT", "FAILED"]):
        return (
            "DEBITED_NOT_CREDITED",
            "Customer account debited at Bank level, but Gateway timed out or Merchant failed to receive credit confirmation.",
            "RECOVERY_REQUIRED",
            "EXCEPTION"
        )

    # Case 4: Gateway & Bank SUCCESS, Merchant record MISSING
    if g_status == "SUCCESS" and b_status in ["SUCCESS", "DEBITED"] and m_status == "MISSING":
        return (
            "RECONCILIATION_EXCEPTION",
            "Gateway and Bank confirmed settlement, but Merchant system record is missing.",
            "RECOVERY_REQUIRED",
            "MISSING_FROM_MERCHANT"
        )

    # Case 2: Clean Failure (Bank NOT debited, Merchant NOT credited)
    if g_status in ["FAILED", "REJECTED"] and b_status in ["NOT_DEBITED", "FAILED"] and m_status in ["NOT_CREDITED", "FAILED"]:
        return (
            "FAILED",
            "Payment failed cleanly at Payment Gateway / NPCI layer without debiting customer account.",
            "NOT_REQUIRED",
            "MATCHED"
        )

    # Pending Case
    if g_status == "PENDING" or b_status == "PENDING" or m_status == "PENDING":
        return (
            "PENDING",
            "Transaction status confirmation pending from Bank or Payment Gateway.",
            "NOT_REQUIRED",
            "UNRESOLVED"
        )

    # General Mismatch
    return (
        "MISMATCH",
        f"Inconsistent state across systems (Gateway: {g_status}, Bank: {b_status}, Merchant: {m_status}).",
        "RECOVERY_REQUIRED",
        "STATUS_MISMATCH"
    )

def get_recommended_action(final_status: str, failure_reason: str) -> str:
    if final_status == "DEBITED_NOT_CREDITED":
        return "Do NOT blindly retry. Verify transaction status with Bank API first, then trigger merchant credit sync or refund."
    elif final_status == "FAILED":
        return "Safe to retry. Customer was not debited."
    elif final_status == "DUPLICATE":
        return "Block automated retry. Mark transaction for manual review to avoid double debit."
    elif final_status == "RECONCILIATION_EXCEPTION":
        return "Sync merchant ledger with gateway settlement log."
    elif final_status == "PENDING":
        return "Poll bank verification status or wait for NPCI callback."
    return "No action required."
