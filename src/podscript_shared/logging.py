"""Structured logging for payment and credit operations."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent.parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

PAYMENT_LOG_FILE = LOGS_DIR / "payment.log"


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for easy parsing."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, default=str)


def _get_payment_logger() -> logging.Logger:
    """Get or create the payment logger with file and console handlers."""
    logger = logging.getLogger("payment")

    # Only configure once
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # File handler - JSON format for parsing
    file_handler = logging.FileHandler(PAYMENT_LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    # Console handler - simple format for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(console_handler)

    return logger


class PaymentLogger:
    """Structured logger for payment and credit operations."""

    def __init__(self):
        self._logger = _get_payment_logger()

    def _log(
        self,
        level: int,
        message: str,
        order_id: Optional[str] = None,
        user_id: Optional[str] = None,
        amount: Optional[int] = None,
        operation: Optional[str] = None,
        status: Optional[str] = None,
        error: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Internal log method with structured data."""
        extra_data: Dict[str, Any] = {}

        if order_id:
            extra_data["order_id"] = order_id
        if user_id:
            extra_data["user_id"] = user_id
        if amount is not None:
            extra_data["amount"] = amount
        if operation:
            extra_data["operation"] = operation
        if status:
            extra_data["status"] = status
        if error:
            extra_data["error"] = error
        if extra:
            extra_data.update(extra)

        record = self._logger.makeRecord(
            self._logger.name,
            level,
            "",
            0,
            message,
            (),
            None,
        )
        record.extra_data = extra_data
        self._logger.handle(record)

    def payment_created(
        self,
        order_id: str,
        user_id: str,
        amount: int,
        payment_method: str,
    ) -> None:
        """Log payment order creation."""
        self._log(
            logging.INFO,
            f"Payment order created: {order_id}",
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            operation="payment_created",
            extra={"payment_method": payment_method},
        )

    def webhook_received(
        self,
        order_id: str,
        trade_no: str,
        trade_status: str,
    ) -> None:
        """Log webhook receipt."""
        self._log(
            logging.INFO,
            f"Webhook received for order: {order_id}",
            order_id=order_id,
            operation="webhook_received",
            extra={"trade_no": trade_no, "trade_status": trade_status},
        )

    def signature_verified(
        self,
        order_id: str,
        success: bool,
    ) -> None:
        """Log signature verification result."""
        level = logging.INFO if success else logging.WARNING
        status = "success" if success else "failed"
        self._log(
            level,
            f"Signature verification {status} for order: {order_id}",
            order_id=order_id,
            operation="signature_verification",
            status=status,
        )

    def credits_added(
        self,
        order_id: str,
        user_id: str,
        amount: int,
        new_balance: int,
    ) -> None:
        """Log successful credit addition."""
        self._log(
            logging.INFO,
            f"Credits added: +{amount} for user {user_id}",
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            operation="credits_added",
            status="success",
            extra={"new_balance": new_balance},
        )

    def credits_deducted(
        self,
        user_id: str,
        amount: int,
        task_id: str,
        new_balance: int,
    ) -> None:
        """Log credit deduction for transcription."""
        self._log(
            logging.INFO,
            f"Credits deducted: -{amount} for user {user_id}",
            user_id=user_id,
            amount=amount,
            operation="credits_deducted",
            status="success",
            extra={"task_id": task_id, "new_balance": new_balance},
        )

    def credits_refunded(
        self,
        user_id: str,
        amount: int,
        task_id: str,
        reason: str,
        new_balance: int,
    ) -> None:
        """Log credit refund due to failure."""
        self._log(
            logging.INFO,
            f"Credits refunded: +{amount} for user {user_id}",
            user_id=user_id,
            amount=amount,
            operation="credits_refunded",
            status="success",
            extra={"task_id": task_id, "reason": reason, "new_balance": new_balance},
        )

    def payment_failed(
        self,
        order_id: str,
        user_id: str,
        error: str,
    ) -> None:
        """Log payment failure."""
        self._log(
            logging.ERROR,
            f"Payment failed for order: {order_id}",
            order_id=order_id,
            user_id=user_id,
            operation="payment_failed",
            status="failed",
            error=error,
        )

    def error(
        self,
        message: str,
        order_id: Optional[str] = None,
        user_id: Optional[str] = None,
        error: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a general error."""
        self._log(
            logging.ERROR,
            message,
            order_id=order_id,
            user_id=user_id,
            error=error,
            extra=extra,
        )


# Singleton instance
payment_logger = PaymentLogger()
