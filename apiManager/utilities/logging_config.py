import logging.config
import os
from typing import Dict, Any


# Platform-specific log routing configuration
PLATFORM_ROUTING_CONFIG = {
    "mobile": {
        "priority": "high",
        "separate_handler": True,
        "include_performance_metrics": True,
        "include_device_details": True,
        "alert_on_errors": True,
        "sample_rate": 1.0,  # Log everything for mobile
    },
    "web": {
        "priority": "medium",
        "separate_handler": True,
        "include_performance_metrics": True,
        "include_device_details": False,
        "alert_on_errors": True,
        "sample_rate": 0.8,  # Sample 80% of web logs
    },
    "desktop": {
        "priority": "low",
        "separate_handler": False,
        "include_performance_metrics": False,
        "include_device_details": False,
        "alert_on_errors": False,
        "sample_rate": 0.5,  # Sample 50% of desktop logs
    },
    "unknown": {
        "priority": "medium",
        "separate_handler": False,
        "include_performance_metrics": False,
        "include_device_details": True,
        "alert_on_errors": True,
        "sample_rate": 1.0,  # Log everything for unknown sources
    },
}

# Enhanced log formatter with platform-aware formatting
ENHANCED_LOG_FORMATTERS = {
    "detailed": {
        "format": "[{asctime}] {levelname} [{name}] [{platform}] [{request_id}] {message}",
        "style": "{",
        "datefmt": "%Y-%m-%d %H:%M:%S",
    },
    "mobile_focused": {
        "format": "[{asctime}] {levelname} [MOBILE:{platform}] [{client_type}] [{request_id}] {message}",
        "style": "{",
        "datefmt": "%Y-%m-%d %H:%M:%S",
    },
    "web_focused": {
        "format": "[{asctime}] {levelname} [WEB:{platform}] [{request_id}] {message}",
        "style": "{",
        "datefmt": "%Y-%m-%d %H:%M:%S",
    },
    "performance": {
        "format": "[{asctime}] {levelname} [PERF:{platform}] [{execution_time_ms}ms] [{request_id}] {message}",
        "style": "{",
        "datefmt": "%Y-%m-%d %H:%M:%S",
    },
}


# Platform-specific log handlers configuration
def get_platform_handlers_config() -> Dict[str, Any]:
    """Generate platform-specific handler configurations"""

    base_handler_config = {
        "class": "logging.StreamHandler",
        "level": "INFO",
        "formatter": "detailed",
    }

    # In production, you might want to use different handlers
    # like FileHandler, RotatingFileHandler, or external log aggregators
    if os.getenv("ENVIRONMENT") == "production":
        base_handler_config.update(
            {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "/var/log/wave/api.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            }
        )

    handlers_config = {
        "default": base_handler_config,
        # Mobile-specific handler
        "mobile": {
            **base_handler_config,
            "formatter": "mobile_focused",
            "level": "DEBUG",  # More verbose for mobile
        },
        # Web-specific handler
        "web": {
            **base_handler_config,
            "formatter": "web_focused",
            "level": "INFO",
        },
        # Performance-focused handler
        "performance": {
            **base_handler_config,
            "formatter": "performance",
            "level": "INFO",
            "filters": ["performance_filter"],
        },
        # Error-only handler for alerts
        "error_alerts": {
            **base_handler_config,
            "formatter": "detailed",
            "level": "ERROR",
        },
    }

    # Add file-based handlers for production
    if os.getenv("ENVIRONMENT") == "production":
        handlers_config["mobile_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/wave/mobile.log",
            "formatter": "mobile_focused",
            "level": "DEBUG",
            "maxBytes": 5242880,  # 5MB
            "backupCount": 3,
        }

        handlers_config["web_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/wave/web.log",
            "formatter": "web_focused",
            "level": "INFO",
            "maxBytes": 5242880,  # 5MB
            "backupCount": 3,
        }

    return handlers_config


# Custom filter for performance logs
class PerformanceFilter(logging.Filter):
    """Filter to only allow performance-related log records"""

    def filter(self, record):
        # Check if record has performance-related attributes
        return (
            hasattr(record, "execution_time_ms")
            or "performance" in getattr(record, "message", "").lower()
            or "timing" in getattr(record, "message", "").lower()
        )


# Complete logging configuration
def get_enhanced_logging_config() -> Dict[str, Any]:
    """Get the complete enhanced logging configuration"""

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": ENHANCED_LOG_FORMATTERS,
        "filters": {
            "performance_filter": {
                "()": PerformanceFilter,
            },
        },
        "handlers": get_platform_handlers_config(),
        "loggers": {
            # Core API loggers with platform routing
            "apiManager.apps.coreAPI.apiLogic": {
                "handlers": ["default", "mobile", "web"],
                "level": "INFO",
                "propagate": False,
            },
            # Platform-specific loggers
            "apiManager.apps.coreAPI.apiLogic.mobile": {
                "handlers": ["mobile"]
                + (["mobile_file"] if os.getenv("ENVIRONMENT") == "production" else []),
                "level": "DEBUG",
                "propagate": False,
            },
            "apiManager.apps.coreAPI.apiLogic.web": {
                "handlers": ["web"]
                + (["web_file"] if os.getenv("ENVIRONMENT") == "production" else []),
                "level": "INFO",
                "propagate": False,
            },
            # Performance logger
            "performance": {
                "handlers": ["performance"],
                "level": "INFO",
                "propagate": False,
            },
            # Error alerts logger
            "error_alerts": {
                "handlers": ["error_alerts"],
                "level": "ERROR",
                "propagate": False,
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["default"],
        },
    }


def setup_enhanced_logging():
    """Setup the enhanced logging configuration"""
    config = get_enhanced_logging_config()
    logging.config.dictConfig(config)

    # Log the setup completion
    logger = logging.getLogger(__name__)
    logger.info("Enhanced logging configuration applied successfully")


def get_platform_config(platform_category: str) -> Dict[str, Any]:
    """Get configuration for a specific platform category"""
    return PLATFORM_ROUTING_CONFIG.get(
        platform_category, PLATFORM_ROUTING_CONFIG["unknown"]
    )


def should_log_for_platform(platform_category: str, level: str = "INFO") -> bool:
    """Determine if we should log for a given platform based on sampling rate"""
    import random

    config = get_platform_config(platform_category)
    sample_rate = config.get("sample_rate", 1.0)

    # Always log errors regardless of sampling
    if level.upper() in ["ERROR", "CRITICAL"]:
        return True

    # Apply sampling rate
    return random.random() < sample_rate
