from langchain_core.tools import tool
from typing import Optional


@tool
def validate_promo_code(promo_code: str, order_id: Optional[str] = None) -> dict:
    """Validate a promotional code and check if it's eligible for use.

    Args:
        promo_code: The promotional code to validate
        order_id: Optional order ID to check code applicability

    Returns:
        Dictionary with validation results including discount amount, expiration, and eligibility
    """
    # Mock data - in production this would query a promotions database
    mock_promo_codes = {
        "FALL50": {
            "code": "FALL50",
            "valid": True,
            "discount_type": "fixed",
            "discount_amount": 50.00,
            "description": "$50 off orders over $500",
            "minimum_purchase": 500.00,
            "expiration_date": "2024-12-31",
            "max_uses": 1000,
            "uses_remaining": 842,
            "eligible_categories": ["Electronics", "Computers", "Accessories"]
        },
        "SAVE20": {
            "code": "SAVE20",
            "valid": True,
            "discount_type": "percentage",
            "discount_amount": 20.0,
            "description": "20% off all orders",
            "minimum_purchase": 0,
            "expiration_date": "2024-11-30",
            "max_uses": 5000,
            "uses_remaining": 3214,
            "eligible_categories": ["All"]
        },
        "EXPIRED10": {
            "code": "EXPIRED10",
            "valid": False,
            "reason": "This promotional code has expired",
            "expiration_date": "2024-01-01"
        }
    }

    promo_code_upper = promo_code.upper()
    promo = mock_promo_codes.get(promo_code_upper)

    if promo:
        return promo
    else:
        return {
            "code": promo_code,
            "valid": False,
            "reason": f"Promotional code '{promo_code}' not found or is invalid"
        }


@tool
def apply_retroactive_discount(order_id: str, promo_code: str) -> dict:
    """Apply a promotional discount retroactively to an already-placed order.

    Args:
        order_id: The order ID to apply the discount to
        promo_code: The promotional code to apply

    Returns:
        Dictionary with application results including adjusted price and refund amount
    """
    # Mock implementation - in production this would update order and process adjustment
    # First validate the promo code
    promo_validation = validate_promo_code(promo_code, order_id)

    if not promo_validation.get("valid"):
        return {
            "success": False,
            "order_id": order_id,
            "promo_code": promo_code,
            "error": promo_validation.get("reason", "Invalid promotional code")
        }

    # Mock order data
    mock_orders = {
        "ORD-12345": {
            "order_id": "ORD-12345",
            "original_total": 1299.00,
            "items_subtotal": 1199.00,
            "eligible_for_promo": True
        }
    }

    order = mock_orders.get(order_id)
    if not order:
        return {
            "success": False,
            "order_id": order_id,
            "error": f"Order {order_id} not found"
        }

    # Check eligibility
    if not order.get("eligible_for_promo"):
        return {
            "success": False,
            "order_id": order_id,
            "promo_code": promo_code,
            "error": "This order is not eligible for promotional discounts"
        }

    # Calculate discount
    discount_amount = 0
    if promo_validation["discount_type"] == "fixed":
        discount_amount = promo_validation["discount_amount"]
    elif promo_validation["discount_type"] == "percentage":
        discount_amount = order["items_subtotal"] * (promo_validation["discount_amount"] / 100)

    # Check minimum purchase requirement
    if order["items_subtotal"] < promo_validation.get("minimum_purchase", 0):
        return {
            "success": False,
            "order_id": order_id,
            "promo_code": promo_code,
            "error": f"Order does not meet minimum purchase requirement of ${promo_validation.get('minimum_purchase', 0):.2f}"
        }

    new_total = order["original_total"] - discount_amount
    refund_amount = discount_amount

    return {
        "success": True,
        "order_id": order_id,
        "promo_code": promo_code,
        "original_total": order["original_total"],
        "discount_amount": round(discount_amount, 2),
        "new_total": round(new_total, 2),
        "refund_amount": round(refund_amount, 2),
        "refund_method": "Original payment method",
        "refund_timeline": "3-5 business days",
        "message": f"Promotional code {promo_code} has been applied successfully. You will receive a refund of ${refund_amount:.2f}."
    }


@tool
def check_loyalty_balance(customer_id: str) -> dict:
    """Check the loyalty points balance for a customer.

    Args:
        customer_id: The customer ID to check loyalty points for

    Returns:
        Dictionary with loyalty balance, tier status, and points expiration info
    """
    # Mock data - in production this would query a loyalty database
    mock_loyalty_accounts = {
        "CUST-001": {
            "customer_id": "CUST-001",
            "points_balance": 2450,
            "points_pending": 120,
            "tier": "Gold",
            "tier_benefits": [
                "Free shipping on all orders",
                "Early access to sales",
                "Birthday bonus points"
            ],
            "next_tier": "Platinum",
            "points_to_next_tier": 550,
            "points_expiring_soon": {
                "amount": 200,
                "expiration_date": "2024-03-31"
            },
            "lifetime_points_earned": 8920
        },
        "CUST-002": {
            "customer_id": "CUST-002",
            "points_balance": 550,
            "points_pending": 0,
            "tier": "Silver",
            "tier_benefits": [
                "Free shipping on orders over $50",
                "Exclusive member discounts"
            ],
            "next_tier": "Gold",
            "points_to_next_tier": 450,
            "points_expiring_soon": None,
            "lifetime_points_earned": 1230
        }
    }

    loyalty_account = mock_loyalty_accounts.get(customer_id)
    if loyalty_account:
        return loyalty_account
    else:
        return {
            "error": f"No loyalty account found for customer ID: {customer_id}",
            "customer_id": customer_id
        }


@tool
def get_loyalty_history(customer_id: str) -> dict:
    """Get the transaction history for a customer's loyalty account.

    Args:
        customer_id: The customer ID to get loyalty history for

    Returns:
        Dictionary with loyalty transaction history including earned and redeemed points
    """
    # Mock data - in production this would query loyalty transaction history
    mock_loyalty_history = {
        "CUST-001": {
            "customer_id": "CUST-001",
            "transactions": [
                {
                    "date": "2024-01-07",
                    "type": "earned",
                    "points": 120,
                    "description": "Purchase - Order ORD-12345",
                    "order_id": "ORD-12345"
                },
                {
                    "date": "2024-01-05",
                    "type": "redeemed",
                    "points": -500,
                    "description": "Redeemed for $25 discount",
                    "order_id": "ORD-11111"
                },
                {
                    "date": "2024-01-01",
                    "type": "earned",
                    "points": 50,
                    "description": "New Year Bonus Points",
                    "order_id": None
                },
                {
                    "date": "2023-12-28",
                    "type": "earned",
                    "points": 200,
                    "description": "Purchase - Order ORD-11000",
                    "order_id": "ORD-11000"
                }
            ],
            "total_earned": 8920,
            "total_redeemed": 6470,
            "current_balance": 2450
        },
        "CUST-002": {
            "customer_id": "CUST-002",
            "transactions": [
                {
                    "date": "2024-01-08",
                    "type": "earned",
                    "points": 60,
                    "description": "Purchase - Order ORD-67890",
                    "order_id": "ORD-67890"
                },
                {
                    "date": "2023-12-15",
                    "type": "earned",
                    "points": 100,
                    "description": "Purchase - Order ORD-55555",
                    "order_id": "ORD-55555"
                }
            ],
            "total_earned": 1230,
            "total_redeemed": 680,
            "current_balance": 550
        }
    }

    history = mock_loyalty_history.get(customer_id)
    if history:
        return history
    else:
        return {
            "error": f"No loyalty history found for customer ID: {customer_id}",
            "customer_id": customer_id
        }


@tool
def calculate_points_earned(order_total: float, customer_tier: str = "Silver") -> dict:
    """Calculate loyalty points that would be earned for a purchase.

    Args:
        order_total: The order total amount
        customer_tier: The customer's loyalty tier (Silver, Gold, Platinum)

    Returns:
        Dictionary with points calculation breakdown
    """
    # Mock calculation - in production this would use actual loyalty program rules
    tier_multipliers = {
        "Silver": 1.0,
        "Gold": 1.5,
        "Platinum": 2.0
    }

    base_points_per_dollar = 1
    multiplier = tier_multipliers.get(customer_tier, 1.0)
    base_points = int(order_total * base_points_per_dollar)
    bonus_points = int(base_points * (multiplier - 1.0))
    total_points = base_points + bonus_points

    return {
        "order_total": order_total,
        "customer_tier": customer_tier,
        "base_points": base_points,
        "tier_multiplier": multiplier,
        "bonus_points": bonus_points,
        "total_points_earned": total_points,
        "points_breakdown": f"${order_total:.2f} x {base_points_per_dollar} point per dollar x {multiplier}x tier bonus = {total_points} points"
    }


@tool
def redeem_loyalty_points(customer_id: str, points_to_redeem: int) -> dict:
    """Redeem loyalty points for a discount or reward.

    Args:
        customer_id: The customer ID redeeming points
        points_to_redeem: The number of points to redeem

    Returns:
        Dictionary with redemption details including discount value
    """
    # Mock implementation - in production this would update loyalty account
    # Check balance first
    balance_info = check_loyalty_balance(customer_id)

    if "error" in balance_info:
        return balance_info

    current_balance = balance_info["points_balance"]

    if points_to_redeem > current_balance:
        return {
            "success": False,
            "customer_id": customer_id,
            "error": f"Insufficient points. You have {current_balance} points but tried to redeem {points_to_redeem} points."
        }

    # Calculate discount value (100 points = $5)
    points_per_dollar = 20
    discount_value = points_to_redeem / points_per_dollar
    new_balance = current_balance - points_to_redeem

    return {
        "success": True,
        "customer_id": customer_id,
        "points_redeemed": points_to_redeem,
        "discount_value": round(discount_value, 2),
        "previous_balance": current_balance,
        "new_balance": new_balance,
        "redemption_code": f"LOYALTY-{customer_id[-3:]}-{points_to_redeem}",
        "message": f"Successfully redeemed {points_to_redeem} points for ${discount_value:.2f} discount. Your new balance is {new_balance} points."
    }
