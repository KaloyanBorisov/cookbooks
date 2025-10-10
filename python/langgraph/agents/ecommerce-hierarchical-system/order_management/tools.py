from langchain_core.tools import tool
from typing import Optional


@tool
def get_order_details(order_id: str) -> dict:
    """Get detailed information about an order.

    Args:
        order_id: The order ID to look up

    Returns:
        Dictionary with order details including items, status, dates, and shipping info
    """
    # Mock data - in production this would query an order database
    mock_orders = {
        "ORD-12345": {
            "order_id": "ORD-12345",
            "status": "processing",
            "order_date": "2024-01-07",
            "customer_id": "CUST-001",
            "items": [
                {
                    "item_id": "ITEM-456",
                    "name": "Laptop - Dell XPS 15",
                    "quantity": 1,
                    "price": 1199.00
                }
            ],
            "subtotal": 1199.00,
            "total": 1299.00,
            "shipping_address": "123 Main St, San Francisco, CA 94102",
            "estimated_delivery": "2024-01-15"
        },
        "ORD-67890": {
            "order_id": "ORD-67890",
            "status": "shipped",
            "order_date": "2024-01-08",
            "customer_id": "CUST-002",
            "items": [
                {
                    "item_id": "ITEM-789",
                    "name": "Wireless Mouse",
                    "quantity": 2,
                    "price": 29.99
                }
            ],
            "subtotal": 59.98,
            "total": 64.78,
            "shipping_address": "456 Oak Ave, Portland, OR 97201",
            "estimated_delivery": "2024-01-12"
        }
    }

    order = mock_orders.get(order_id)
    if order:
        return order
    else:
        return {
            "error": f"No order found with ID: {order_id}",
            "order_id": order_id
        }


@tool
def track_shipment(order_id: str) -> dict:
    """Track the shipping status and location of an order.

    Args:
        order_id: The order ID to track

    Returns:
        Dictionary with shipment tracking details including carrier, tracking number, and current location
    """
    # Mock data - in production this would integrate with shipping carriers
    mock_shipments = {
        "ORD-12345": {
            "order_id": "ORD-12345",
            "status": "processing",
            "tracking_number": None,
            "carrier": None,
            "current_location": "Warehouse - San Jose, CA",
            "last_update": "2024-01-09T14:30:00Z",
            "message": "Order is being prepared for shipment",
            "tracking_history": [
                {"date": "2024-01-07", "status": "Order received", "location": "Online"},
                {"date": "2024-01-09", "status": "Processing", "location": "Warehouse - San Jose, CA"}
            ]
        },
        "ORD-67890": {
            "order_id": "ORD-67890",
            "status": "in_transit",
            "tracking_number": "1Z999AA10123456784",
            "carrier": "UPS",
            "current_location": "Sacramento, CA",
            "last_update": "2024-01-10T08:15:00Z",
            "estimated_delivery": "2024-01-12",
            "message": "Package is in transit to destination",
            "tracking_history": [
                {"date": "2024-01-08", "status": "Shipped", "location": "San Jose, CA"},
                {"date": "2024-01-09", "status": "In transit", "location": "Oakland, CA"},
                {"date": "2024-01-10", "status": "In transit", "location": "Sacramento, CA"}
            ]
        }
    }

    shipment = mock_shipments.get(order_id)
    if shipment:
        return shipment
    else:
        return {
            "error": f"No shipment information found for order ID: {order_id}",
            "order_id": order_id
        }


@tool
def check_fulfillment_status(order_id: str) -> dict:
    """Check the fulfillment status of an order in the warehouse.

    Args:
        order_id: The order ID to check fulfillment status for

    Returns:
        Dictionary with fulfillment details including picking, packing, and readiness status
    """
    # Mock data - in production this would query warehouse management system
    mock_fulfillment = {
        "ORD-12345": {
            "order_id": "ORD-12345",
            "fulfillment_status": "picking_in_progress",
            "warehouse_location": "Warehouse A - San Jose, CA",
            "assigned_picker": "Picker-42",
            "picking_progress": "60%",
            "items_picked": 0,
            "items_total": 1,
            "estimated_ready_date": "2024-01-11",
            "notes": "Item located in aisle 12. High-value item requires special handling.",
            "stages": {
                "received": True,
                "picking": True,
                "packing": False,
                "ready_to_ship": False
            }
        },
        "ORD-67890": {
            "order_id": "ORD-67890",
            "fulfillment_status": "shipped",
            "warehouse_location": "Warehouse A - San Jose, CA",
            "assigned_picker": "Picker-15",
            "picking_progress": "100%",
            "items_picked": 2,
            "items_total": 2,
            "ship_date": "2024-01-08",
            "notes": "Order fulfilled and shipped successfully",
            "stages": {
                "received": True,
                "picking": True,
                "packing": True,
                "ready_to_ship": True,
                "shipped": True
            }
        }
    }

    fulfillment = mock_fulfillment.get(order_id)
    if fulfillment:
        return fulfillment
    else:
        return {
            "error": f"No fulfillment information found for order ID: {order_id}",
            "order_id": order_id
        }


@tool
def cancel_order(order_id: str, reason: str) -> dict:
    """Cancel an order if it hasn't been shipped yet.

    Args:
        order_id: The order ID to cancel
        reason: The reason for cancellation

    Returns:
        Dictionary with cancellation status and details
    """
    # Mock implementation - in production this would update order database
    # Check if order can be cancelled (not shipped yet)
    mock_order_statuses = {
        "ORD-12345": "processing",
        "ORD-67890": "shipped"
    }

    status = mock_order_statuses.get(order_id)

    if not status:
        return {
            "success": False,
            "error": f"Order {order_id} not found",
            "order_id": order_id
        }

    if status == "shipped":
        return {
            "success": False,
            "order_id": order_id,
            "message": "Order has already been shipped and cannot be cancelled. Please initiate a return instead.",
            "status": status
        }

    return {
        "success": True,
        "order_id": order_id,
        "cancellation_id": f"CANCEL-{order_id[-5:]}",
        "reason": reason,
        "refund_status": "pending",
        "refund_timeline": "3-5 business days",
        "message": f"Order {order_id} has been successfully cancelled. Refund will be processed within 3-5 business days."
    }


@tool
def update_shipping_address(order_id: str, new_address: str) -> dict:
    """Update the shipping address for an order if it hasn't shipped yet.

    Args:
        order_id: The order ID to update
        new_address: The new shipping address

    Returns:
        Dictionary with update status and confirmation
    """
    # Mock implementation - in production this would update order database
    mock_order_statuses = {
        "ORD-12345": "processing",
        "ORD-67890": "shipped"
    }

    status = mock_order_statuses.get(order_id)

    if not status:
        return {
            "success": False,
            "error": f"Order {order_id} not found",
            "order_id": order_id
        }

    if status == "shipped":
        return {
            "success": False,
            "order_id": order_id,
            "message": "Order has already been shipped. Address cannot be changed. Please contact carrier for address correction.",
            "status": status
        }

    return {
        "success": True,
        "order_id": order_id,
        "old_address": "123 Main St, San Francisco, CA 94102",
        "new_address": new_address,
        "message": f"Shipping address for order {order_id} has been successfully updated."
    }


@tool
def get_delivery_estimate(order_id: str) -> dict:
    """Get estimated delivery date for an order.

    Args:
        order_id: The order ID to get delivery estimate for

    Returns:
        Dictionary with delivery estimate details
    """
    # Mock data - in production this would integrate with shipping systems
    mock_estimates = {
        "ORD-12345": {
            "order_id": "ORD-12345",
            "estimated_delivery_date": "2024-01-15",
            "estimated_delivery_window": "Jan 15-17, 2024",
            "shipping_method": "Standard Shipping (5-7 business days)",
            "current_status": "Processing",
            "can_expedite": True,
            "expedite_options": [
                {"method": "2-Day", "cost": 15.00, "delivery_date": "2024-01-12"},
                {"method": "Overnight", "cost": 25.00, "delivery_date": "2024-01-11"}
            ]
        },
        "ORD-67890": {
            "order_id": "ORD-67890",
            "estimated_delivery_date": "2024-01-12",
            "estimated_delivery_window": "Jan 12, 2024",
            "shipping_method": "Standard Shipping (5-7 business days)",
            "current_status": "In Transit",
            "tracking_number": "1Z999AA10123456784",
            "can_expedite": False,
            "message": "Package is already in transit. Delivery estimate is based on current shipping progress."
        }
    }

    estimate = mock_estimates.get(order_id)
    if estimate:
        return estimate
    else:
        return {
            "error": f"No delivery estimate available for order ID: {order_id}",
            "order_id": order_id
        }
