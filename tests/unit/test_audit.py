#!/usr/bin/env python3
"""Unit tests for audit logging functionality."""

import os
import sys
import unittest
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from coach.audit import AuditLogger
from coach.models import UserContext


class TestAuditLogger(unittest.TestCase):
    """Test audit logging functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary audit log file
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test_audit.log")
        self.audit_logger = AuditLogger(log_file=self.log_file)
        
        # Create test user context
        self.user_context = UserContext(
            user_id="test_user_123",
            email="test@example.com",
            name="Test User",
            oauth_token="test_oauth_token",
            refresh_token="test_refresh_token"
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_encryption_operation(self):
        """Test logging encryption operations."""
        # Log successful encryption
        self.audit_logger.log_encryption_operation(
            user_id=self.user_context.user_id,
            operation="encrypt_file",
            file_path="/test/file.txt",
            data_size=1024,
            success=True
        )
        
        # Log failed encryption
        self.audit_logger.log_encryption_operation(
            user_id=self.user_context.user_id,
            operation="decrypt_file",
            file_path="/test/file.enc",
            success=False,
            error="Invalid key"
        )
        
        # Verify logs were written
        self.assertTrue(os.path.exists(self.log_file))
        
        # Read and verify log entries
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
        
        self.assertEqual(len(lines), 2)
        
        # Parse first log entry
        log1 = json.loads(lines[0])
        self.assertEqual(log1['event'], 'encryption_operation')
        self.assertEqual(log1['user_id'], self.user_context.user_id)
        self.assertEqual(log1['operation'], 'encrypt_file')
        self.assertEqual(log1['data_size'], 1024)
        self.assertTrue(log1['success'])
        
        # Parse second log entry
        log2 = json.loads(lines[1])
        self.assertEqual(log2['event'], 'encryption_operation')
        self.assertEqual(log2['operation'], 'decrypt_file')
        self.assertFalse(log2['success'])
        self.assertEqual(log2['error'], 'Invalid key')
    
    def test_log_authentication(self):
        """Test logging authentication events."""
        # Log successful login
        self.audit_logger.log_authentication(
            user_id=self.user_context.user_id,
            action="login",
            success=True,
            method="oauth2_google",
            ip_address="192.168.1.100"
        )
        
        # Log failed password verification
        self.audit_logger.log_authentication(
            user_id=self.user_context.user_id,
            action="password_verify",
            success=False,
            method="encryption_manager"
        )
        
        # Verify logs
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
        
        self.assertEqual(len(lines), 2)
        
        # Verify login event
        log1 = json.loads(lines[0])
        self.assertEqual(log1['event'], 'authentication')
        self.assertEqual(log1['action'], 'login')
        self.assertTrue(log1['success'])
        self.assertEqual(log1['ip_address'], '192.168.1.100')
    
    def test_log_storage_access(self):
        """Test logging storage access events."""
        self.audit_logger.log_storage_access(
            user_id=self.user_context.user_id,
            operation="upload_encrypted",
            provider="GCPStorageProvider",
            remote_path="user_data/file.enc",
            success=True,
            data_size=2048
        )
        
        # Verify log
        with open(self.log_file, 'r') as f:
            log = json.loads(f.readline())
        
        self.assertEqual(log['event'], 'storage_access')
        self.assertEqual(log['operation'], 'upload_encrypted')
        self.assertEqual(log['provider'], 'GCPStorageProvider')
        self.assertEqual(log['data_size'], 2048)
    
    def test_log_rate_limit(self):
        """Test logging rate limit events."""
        self.audit_logger.log_rate_limit(
            user_id=self.user_context.user_id,
            operation="encrypt_file",
            allowed=False,
            wait_time=10.5
        )
        
        # Verify log
        with open(self.log_file, 'r') as f:
            log = json.loads(f.readline())
        
        self.assertEqual(log['event'], 'rate_limit')
        self.assertEqual(log['operation'], 'encrypt_file')
        self.assertFalse(log['allowed'])
        self.assertEqual(log['wait_time'], 10.5)
    
    def test_log_security_event(self):
        """Test logging general security events."""
        self.audit_logger.log_security_event(
            event_type="suspicious_activity",
            severity="warning",
            user_id=self.user_context.user_id,
            description="Multiple failed login attempts",
            ip_address="192.168.1.100",
            attempts=5
        )
        
        # Verify log
        with open(self.log_file, 'r') as f:
            log = json.loads(f.readline())
        
        self.assertEqual(log['event'], 'security_event')
        self.assertEqual(log['security_event_type'], 'suspicious_activity')
        self.assertEqual(log['severity'], 'warning')
        self.assertEqual(log['attempts'], 5)
    
    def test_search_logs(self):
        """Test searching audit logs."""
        # Create multiple log entries
        self.audit_logger.log_authentication(
            user_id="user1",
            action="login",
            success=True
        )
        
        self.audit_logger.log_authentication(
            user_id="user2",
            action="login",
            success=True
        )
        
        self.audit_logger.log_encryption_operation(
            user_id="user1",
            operation="encrypt_file",
            success=True
        )
        
        # Search by user ID
        results = self.audit_logger.search_logs(user_id="user1")
        self.assertEqual(len(results), 2)
        
        # Search by event type
        results = self.audit_logger.search_logs(event_type="authentication")
        self.assertEqual(len(results), 2)
        
        # Search with limit
        results = self.audit_logger.search_logs(limit=1)
        self.assertEqual(len(results), 1)
    
    def test_search_logs_by_time(self):
        """Test searching logs by time range."""
        # Create log entries
        self.audit_logger.log_authentication(
            user_id="user1",
            action="login",
            success=True
        )
        
        # Search with time range
        start_time = datetime.utcnow() - timedelta(minutes=5)
        end_time = datetime.utcnow() + timedelta(minutes=5)
        
        results = self.audit_logger.search_logs(
            start_time=start_time,
            end_time=end_time
        )
        self.assertEqual(len(results), 1)
        
        # Search outside time range
        old_start = datetime.utcnow() - timedelta(days=2)
        old_end = datetime.utcnow() - timedelta(days=1)
        
        results = self.audit_logger.search_logs(
            start_time=old_start,
            end_time=old_end
        )
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()