"""
Centralized Logging System with Multiple Log Files
Tracks execution, errors, and performance metrics for concurrent operations
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
import time
import traceback
from logging.handlers import RotatingFileHandler


class AnalyticsLogger:
    """
    Centralized logger for analytics tracking
    Creates multiple log files for different purposes with rotation
    """
    
    def __init__(self, log_dir: str = "logs"):
        """Initialize logger with multiple handlers"""
        self.log_dir = log_dir
        self._ensure_log_directory()
        self.logger = self._setup_logger()
    
    def _ensure_log_directory(self):
        """Create logs directory if it doesn't exist"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def _setup_logger(self):
        """Setup logging configuration with multiple handlers"""
        # Create logger
        logger = logging.getLogger('analytics_tracker')
        logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        logger.handlers = []
        
        # Formatter
        detailed_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # === 1. MAIN LOG FILE (all levels) ===
        main_handler = RotatingFileHandler(
            os.path.join(self.log_dir, 'analytics.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(detailed_formatter)
        logger.addHandler(main_handler)
        
        # === 2. CONCURRENT EXECUTION LOG (track parallel operations) ===
        concurrent_handler = RotatingFileHandler(
            os.path.join(self.log_dir, 'concurrent_execution.log'),
            maxBytes=10*1024*1024,
            backupCount=3
        )
        concurrent_handler.setLevel(logging.INFO)
        concurrent_handler.setFormatter(detailed_formatter)
        concurrent_handler.addFilter(self._create_filter('concurrent'))
        logger.addHandler(concurrent_handler)
        
        # === 3. ERROR LOG (errors and critical only) ===
        error_handler = RotatingFileHandler(
            os.path.join(self.log_dir, 'errors.log'),
            maxBytes=10*1024*1024,
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        logger.addHandler(error_handler)
        
        # === 4. CONSOLE OUTPUT (INFO and above) ===
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def _create_filter(self, keyword: str):
        """Create a filter for specific log messages"""
        class KeywordFilter(logging.Filter):
            def filter(self, record):
                return keyword.lower() in record.getMessage().lower()
        return KeywordFilter()
    
    def log_concurrent_execution(self, service: str, status: str, time_ms: int, extra: Dict = None):
        """Log concurrent execution with special marker"""
        message = f"[CONCURRENT] {service}: {status} ({time_ms}ms)"
        if extra:
            extra_str = " | ".join([f"{k}={v}" for k, v in extra.items()])
            message += f" | {extra_str}"
        self.logger.info(message)
    
    def log_info(self, message: str, extra: Dict[str, Any] = None):
        """Log info message"""
        log_message = self._format_message(message, extra)
        self.logger.info(log_message)
    
    def log_warning(self, message: str, extra: Dict[str, Any] = None):
        """Log warning message"""
        log_message = self._format_message(message, extra)
        self.logger.warning(log_message)
    
    def log_error(self, message: str, error: Exception = None, extra: Dict[str, Any] = None):
        """Log error message"""
        log_message = self._format_message(message, extra)
        if error:
            log_message += f" | Error: {str(error)}"
        self.logger.error(log_message)
    
    def log_critical(self, message: str, error: Exception = None, extra: Dict[str, Any] = None):
        """Log critical error with traceback"""
        log_message = self._format_message(message, extra)
        if error:
            log_message += f" | Error: {str(error)}"
            log_message += f"\nTraceback: {traceback.format_exc()}"
        self.logger.critical(log_message)
    
    def _format_message(self, message: str, extra: Dict[str, Any] = None) -> str:
        """Format log message with extra data"""
        if extra:
            extra_str = " | ".join([f"{k}={v}" for k, v in extra.items()])
            return f"{message} | {extra_str}"
        return message
    
    def log_execution(self, 
                     query: str,
                     status: str,
                     execution_time_ms: int,
                     service: str = "system",
                     error: Exception = None):
        """
        Log execution details
        
        Args:
            query: Search query processed
            status: success, failed, timeout
            execution_time_ms: Time taken in milliseconds
            service: Service name (serpapi, gemini, database)
            error: Exception if failed
        """
        extra = {
            "query": query,
            "service": service,
            "status": status,
            "time_ms": execution_time_ms
        }
        
        if status == "success":
            self.log_info(f"{service} execution completed", extra)
        elif status == "failed":
            self.log_error(f"{service} execution failed", error, extra)
        elif status == "timeout":
            self.log_warning(f"{service} execution timeout", extra)


class ExecutionTracker:
    """
    Track execution time and status for services
    """
    
    def __init__(self, logger: AnalyticsLogger):
        self.logger = logger
        self.execution_data = {}
    
    def track_service(self, service_name: str):
        """
        Decorator to track service execution
        
        Usage:
            @tracker.track_service('serpapi')
            def fetch_data():
                ...
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                service_status = "success"
                error = None
                result = None
                
                try:
                    result = func(*args, **kwargs)
                    return result
                    
                except Exception as e:
                    service_status = "failed"
                    error = e
                    raise e
                    
                finally:
                    end_time = time.time()
                    execution_time_ms = int((end_time - start_time) * 1000)
                    
                    # Store execution data
                    self.execution_data[service_name] = {
                        "status": service_status,
                        "time_ms": execution_time_ms,
                        "error": error
                    }
                    
                    # Log concurrent execution with special marker
                    # Try to extract query from kwargs or args (skip 'self' at args[0])
                    query = kwargs.get('query', kwargs.get('prompt', args[1] if len(args) > 1 else 'N/A'))
                    self.logger.log_concurrent_execution(
                        service=service_name,
                        status=service_status,
                        time_ms=execution_time_ms,
                        extra={'query': str(query)[:50]}  # Truncate long queries
                    )
                    
                    # Log execution
                    self.logger.log_execution(
                        query=str(query),
                        status=service_status,
                        execution_time_ms=execution_time_ms,
                        service=service_name,
                        error=error
                    )
            
            return wrapper
        return decorator
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get summary of all tracked executions
        
        Returns:
            {
                'serpapi': {'status': 'success', 'time_ms': 1234},
                'gemini': {'status': 'success', 'time_ms': 567},
                'total_time_ms': 1801
            }
        """
        total_time = sum(
            data['time_ms'] 
            for data in self.execution_data.values()
        )
        
        summary = self.execution_data.copy()
        summary['total_time_ms'] = total_time
        
        return summary
    
    def get_log_data(self, query: str) -> Dict[str, Any]:
        """
        Get structured data for ExecutionLog table
        
        Returns data formatted for database insertion
        """
        summary = self.get_execution_summary()
        
        return {
            'query': query,
            'timestamp': datetime.utcnow(),
            'serpapi_status': summary.get('serpapi', {}).get('status', 'not_run'),
            'gemini_status': summary.get('gemini', {}).get('status', 'not_run'),
            'database_status': summary.get('database', {}).get('status', 'not_run'),
            'serpapi_time_ms': summary.get('serpapi', {}).get('time_ms', 0),
            'gemini_time_ms': summary.get('gemini', {}).get('time_ms', 0),
            'database_time_ms': summary.get('database', {}).get('time_ms', 0),
            'total_time_ms': summary.get('total_time_ms', 0),
            'log_level': self._determine_log_level(summary),
            'error_service': self._get_error_service(summary),
            'error_message': self._get_error_message(summary),
            'error_traceback': self._get_error_traceback(summary)
        }
    
    def _determine_log_level(self, summary: Dict[str, Any]) -> str:
        """Determine log level based on execution status"""
        statuses = [
            data.get('status') 
            for key, data in summary.items() 
            if isinstance(data, dict) and 'status' in data
        ]
        
        if 'failed' in statuses:
            # Check if critical service failed
            if summary.get('serpapi', {}).get('status') == 'failed':
                return 'CRITICAL'
            return 'ERROR'
        elif 'timeout' in statuses:
            return 'WARNING'
        else:
            return 'INFO'
    
    def _get_error_service(self, summary: Dict[str, Any]) -> Optional[str]:
        """Get which service failed"""
        for service, data in summary.items():
            if isinstance(data, dict) and data.get('status') == 'failed':
                return service
        return None
    
    def _get_error_message(self, summary: Dict[str, Any]) -> Optional[str]:
        """Get error message from failed service"""
        for service, data in summary.items():
            if isinstance(data, dict) and data.get('error'):
                return str(data['error'])
        return None
    
    def _get_error_traceback(self, summary: Dict[str, Any]) -> Optional[str]:
        """Get error traceback if available"""
        for service, data in summary.items():
            if isinstance(data, dict) and data.get('error'):
                return traceback.format_exc()
        return None
    
    def reset(self):
        """Reset execution tracking data"""
        self.execution_data = {}


# Global instances
analytics_logger = AnalyticsLogger(log_dir='logs')
execution_tracker = ExecutionTracker(analytics_logger)
