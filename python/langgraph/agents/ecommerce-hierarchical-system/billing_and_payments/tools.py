from langchain_core.tools import tool
from typing import Optional


@tool
def lookup_transaction(order_id: str) -> dict:
    """Look up transaction details by order ID.

    Args:
        order_id: The order ID to look up transaction for

    Returns:
        Dictionary with transaction details including transaction_id, amount_charged, payment_method
    """
    # Mock data - in production this would query a payment gateway/database
    mock_transactions = {
        "ORD-12345": {
            "transaction_id": "TXN-98765",
            "order_id": "ORD-12345",
            "amount_charged": 1299.00,
            "currency": "USD",
            "payment_method": "Visa ****1234",
            "transaction_date": "2024-01-07",
            "status": "completed"
        },
        "ORD-67890": {
            "transaction_id": "TXN-54321",
            "order_id": "ORD-67890",
            "amount_charged": 599.99,
            "currency": "USD",
            "payment_method": "MasterCard ****5678",
            "transaction_date": "2024-01-08",
            "status": "completed"
        }
    }

    transaction = mock_transactions.get(order_id)
    if transaction:
        return transaction
    else:
        return {
            "error": f"No transaction found for order ID: {order_id}",
            "order_id": order_id
        }


@tool
def verify_pricing(order_id: str, expected_amount: float) -> dict:
    """Verify if the charged amount matches the expected price for an order.

    Args:
        order_id: The order ID to verify pricing for
        expected_amount: The expected/advertised price

    Returns:
        Dictionary with verification results including discrepancy details
    """
    # Mock data - in production this would check order details and pricing rules
    mock_order_pricing = {
        "ORD-12345": {
            "order_id": "ORD-12345",
            "advertised_price": 1199.00,
            "charged_amount": 1299.00,
            "discrepancy": 100.00,
            "reason": "Tax and shipping not included in advertised price",
            "breakdown": {
                "base_price": 1199.00,
                "tax": 95.92,
                "shipping": 4.08
            }
        },
        "ORD-67890": {
            "order_id": "ORD-67890",
            "advertised_price": 599.99,
            "charged_amount": 599.99,
            "discrepancy": 0.00,
            "reason": "Price matches advertised amount",
            "breakdown": {
                "base_price": 549.99,
                "tax": 50.00,
                "shipping": 0.00
            }
        }
    }

    pricing_info = mock_order_pricing.get(order_id)
    if pricing_info:
        # Check if expected amount matches
        if abs(pricing_info["advertised_price"] - expected_amount) < 0.01:
            return pricing_info
        else:
            pricing_info["note"] = f"Expected amount {expected_amount} doesn't match our records"
            return pricing_info
    else:
        return {
            "error": f"No pricing information found for order ID: {order_id}",
            "order_id": order_id,
            "expected_amount": expected_amount
        }


@tool
def process_refund(order_id: str, amount: float, reason: str) -> dict:
    """Process a refund for an order.

    Args:
        order_id: The order ID to process refund for
        amount: The refund amount
        reason: The reason for the refund

    Returns:
        Dictionary with refund processing results
    """
    # Mock implementation - in production this would integrate with payment processor
    return {
        "refund_id": f"REF-{order_id[-5:]}",
        "order_id": order_id,
        "amount": amount,
        "reason": reason,
        "status": "processed",
        "estimated_days": "3-5 business days",
        "message": f"Refund of ${amount:.2f} has been processed successfully"
    }


@tool
def calculate_price_adjustment(
    original_amount: float,
    discount_amount: float,
    tax_rate: float = 0.08
) -> dict:
    """Calculate the final price after applying a discount and recalculating tax.

    Args:
        original_amount: The original charged amount
        discount_amount: The discount amount to apply
        tax_rate: Tax rate to apply (default 8%)

    Returns:
        Dictionary with adjusted pricing breakdown
    """
    # Calculate new totals
    base_with_discount = original_amount - discount_amount
    new_tax = base_with_discount * tax_rate
    new_total = base_with_discount + new_tax
    adjustment_needed = original_amount - new_total

    return {
        "original_amount": original_amount,
        "discount_applied": discount_amount,
        "new_base": base_with_discount,
        "new_tax": round(new_tax, 2),
        "new_total": round(new_total, 2),
        "adjustment_amount": round(adjustment_needed, 2),
        "message": f"Customer should receive ${adjustment_needed:.2f} back"
    }
