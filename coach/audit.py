"""Audit logging for security-sensitive operations."""

import structlog
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import os

from coach.models import UserContext
from coach.config import config


# Configure structured logging
audit_logger = structlog.get_logger("security.audit")


class AuditLogger:
    """Centralized audit logging for security operations."""
    
    def __init__(self, log_file: Optional[str] = None):
        """Initialize audit logger.
        
        Args:
            log_file: Optional path to audit log file
        """
        self.log_file = log_file or os.path.join(
            config.USER_DATA_ROOT,
            "audit",
            "security_audit.log"
        )
        
        # Ensure audit directory exists
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Configure file logging
        self._configure_logging()
    
    def _configure_logging(self):
        """Configure structured logging with file output."""
        # Add file processor to write audit logs
        import logging
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    def _write_log_entry(self, event_type: str, **data):
        """Write log entry directly to file."""
        entry = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            **data
        }
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def log_encryption_operation(
        self,
        user_id: str,
        operation: str,
        file_path: Optional[str] = None,
        data_size: Optional[int] = None,
        success: bool = True,
        error: Optional[str] = None,
        **kwargs
    ):
        """Log encryption/decryption operations.
        
        Args:
            user_id: User performing the operation
            operation: Operation type (encrypt_file, decrypt_file, etc.)
            file_path: Path to file being processed
            data_size: Size of data being processed
            success: Whether operation succeeded
            error: Error message if failed
            **kwargs: Additional context
        """
        self._write_log_entry(
            "encryption_operation",
            user_id=user_id,
            operation=operation,
            file_path=file_path,
            data_size=data_size,
            success=success,
            error=error,
            **kwargs
        )
        
        audit_logger.info(
            "encryption_operation",
            user_id=user_id,
            operation=operation,
            file_path=file_path,
            data_size=data_size,
            success=success,
            error=error,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_key_derivation(
        self,
        user_id: str,
        purpose: str,
        cached: bool = False,
        ttl_minutes: Optional[int] = None,
        **kwargs
    ):
        """Log key derivation operations.
        
        Args:
            user_id: User for whom key is derived
            purpose: Purpose of key derivation
            cached: Whether key was retrieved from cache
            ttl_minutes: TTL for cached key
            **kwargs: Additional context
        """
        audit_logger.info(
            "key_derivation",
            user_id=user_id,
            purpose=purpose,
            cached=cached,
            ttl_minutes=ttl_minutes,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_authentication(
        self,
        user_id: str,
        action: str,
        success: bool = True,
        method: Optional[str] = None,
        ip_address: Optional[str] = None,
        **kwargs
    ):
        """Log authentication events.
        
        Args:
            user_id: User authenticating
            action: Action type (login, logout, password_verify, etc.)
            success: Whether authentication succeeded
            method: Authentication method used
            ip_address: Client IP address
            **kwargs: Additional context
        """
        self._write_log_entry(
            "authentication",
            user_id=user_id,
            action=action,
            success=success,
            method=method,
            ip_address=ip_address,
            **kwargs
        )
        
        audit_logger.info(
            "authentication",
            user_id=user_id,
            action=action,
            success=success,
            method=method,
            ip_address=ip_address,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_storage_access(
        self,
        user_id: str,
        operation: str,
        provider: str,
        remote_path: str,
        success: bool = True,
        data_size: Optional[int] = None,
        error: Optional[str] = None,
        **kwargs
    ):
        """Log cloud storage access.
        
        Args:
            user_id: User performing the operation
            operation: Operation type (upload, download, delete, etc.)
            provider: Storage provider (local, gcp, etc.)
            remote_path: Path in storage
            success: Whether operation succeeded
            data_size: Size of data transferred
            error: Error message if failed
            **kwargs: Additional context
        """
        self._write_log_entry(
            "storage_access",
            user_id=user_id,
            operation=operation,
            provider=provider,
            remote_path=remote_path,
            success=success,
            data_size=data_size,
            error=error,
            **kwargs
        )
        
        audit_logger.info(
            "storage_access",
            user_id=user_id,
            operation=operation,
            provider=provider,
            remote_path=remote_path,
            success=success,
            data_size=data_size,
            error=error,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_rate_limit(
        self,
        user_id: str,
        operation: str,
        allowed: bool,
        wait_time: Optional[float] = None,
        **kwargs
    ):
        """Log rate limiting events.
        
        Args:
            user_id: User being rate limited
            operation: Operation being limited
            allowed: Whether operation was allowed
            wait_time: Time to wait if limited
            **kwargs: Additional context
        """
        self._write_log_entry(
            "rate_limit",
            user_id=user_id,
            operation=operation,
            allowed=allowed,
            wait_time=wait_time,
            **kwargs
        )
        
        audit_logger.info(
            "rate_limit",
            user_id=user_id,
            operation=operation,
            allowed=allowed,
            wait_time=wait_time,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        user_id: Optional[str] = None,
        description: str = "",
        **kwargs
    ):
        """Log general security events.
        
        Args:
            event_type: Type of security event
            severity: Severity level (info, warning, error, critical)
            user_id: User involved (if applicable)
            description: Event description
            **kwargs: Additional context
        """
        # Write log entry - rename event_type to security_event_type to avoid conflict
        data = {
            "security_event_type": event_type,
            "severity": severity,
            "user_id": user_id,
            "description": description,
            **kwargs
        }
        self._write_log_entry("security_event", **data)
        
        # Map severity string to log method
        log_method = {
            "info": audit_logger.info,
            "warning": audit_logger.warning,
            "error": audit_logger.error,
            "critical": audit_logger.critical
        }.get(severity.lower(), audit_logger.warning)
        
        log_method(
            "security_event",
            event_type=event_type,
            user_id=user_id,
            description=description,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def search_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> list[Dict[str, Any]]:
        """Search audit logs.
        
        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum results to return
            
        Returns:
            List of matching log entries
        """
        results = []
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        
                        # Apply filters
                        if user_id and entry.get('user_id') != user_id:
                            continue
                        
                        if event_type and entry.get('event') != event_type:
                            continue
                        
                        if start_time or end_time:
                            entry_time = datetime.fromisoformat(
                                entry.get('timestamp', '').replace('Z', '+00:00')
                            )
                            if start_time and entry_time < start_time:
                                continue
                            if end_time and entry_time > end_time:
                                continue
                        
                        results.append(entry)
                        
                        if len(results) >= limit:
                            break
                            
                    except (json.JSONDecodeError, KeyError):
                        # Skip malformed entries
                        continue
                        
        except FileNotFoundError:
            # No audit log yet
            pass
        
        return results


# Global audit logger instance
audit = AuditLogger()