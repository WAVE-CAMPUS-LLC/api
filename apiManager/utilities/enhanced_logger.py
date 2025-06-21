import logging
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from opentelemetry.trace import get_current_span
from .logging_config import get_platform_config, should_log_for_platform


class EnhancedLogger:
    """Enhanced logger with automatic enrichment and platform-based routing"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.start_time = None

    def _get_enriched_data(
        self,
        platform: Optional[str] = None,
        device_info: Optional[Dict] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate enriched log data with automatic fields"""

        # Get OpenTelemetry span data
        span = get_current_span()
        trace_id = None
        span_id = None

        if span and span.is_recording():
            span_context = span.get_span_context()
            trace_id = (
                format(span_context.trace_id, "032x") if span_context.trace_id else None
            )
            span_id = (
                format(span_context.span_id, "016x") if span_context.span_id else None
            )

        enriched_data = {
            # Core identification
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id or str(uuid.uuid4()),
            # Platform routing data
            "platform": self._normalize_platform(platform),
            "platform_category": self._categorize_platform(platform),
            # Tracing data
            "trace_id": trace_id,
            "span_id": span_id,
            # Device and client data
            "device_info": device_info or {},
            "user_agent": user_agent,
            "client_type": self._detect_client_type(user_agent, device_info),
            # Performance data
            "execution_time_ms": (
                self._get_execution_time() if self.start_time else None
            ),
            # Additional context
            **kwargs,
        }

        return {k: v for k, v in enriched_data.items() if v is not None}

    def _normalize_platform(self, platform: Optional[str]) -> str:
        """Normalize platform string for consistent routing"""
        if not platform:
            return "unknown"

        platform_lower = platform.lower()

        # Mobile platforms
        if any(mobile in platform_lower for mobile in ["ios", "iphone", "ipad"]):
            return "ios"
        elif any(android in platform_lower for android in ["android", "droid"]):
            return "android"

        # Web platforms
        elif any(
            web in platform_lower
            for web in ["web", "browser", "chrome", "firefox", "safari", "edge"]
        ):
            return "web"

        # Desktop platforms
        elif any(
            desktop in platform_lower
            for desktop in ["windows", "macos", "mac", "linux", "desktop"]
        ):
            return "desktop"

        return platform_lower

    def _categorize_platform(self, platform: Optional[str]) -> str:
        """Categorize platform for routing decisions"""
        normalized = self._normalize_platform(platform)

        if normalized in ["ios", "android"]:
            return "mobile"
        elif normalized == "web":
            return "web"
        elif normalized == "desktop":
            return "desktop"
        else:
            return "unknown"

    def _detect_client_type(
        self, user_agent: Optional[str], device_info: Optional[Dict]
    ) -> str:
        """Detect client type from user agent and device info"""
        if not user_agent:
            return "unknown"

        user_agent_lower = user_agent.lower()

        # Mobile apps
        if "wave" in user_agent_lower or "mobile-app" in user_agent_lower:
            return "mobile_app"

        # Mobile browsers
        elif any(
            mobile in user_agent_lower
            for mobile in ["mobile", "android", "iphone", "ipad"]
        ):
            return "mobile_browser"

        # Desktop browsers
        elif any(
            browser in user_agent_lower
            for browser in ["chrome", "firefox", "safari", "edge"]
        ):
            return "desktop_browser"

        # API clients
        elif any(
            api in user_agent_lower
            for api in ["postman", "curl", "httpie", "python", "requests"]
        ):
            return "api_client"

        return "unknown"

    def _get_execution_time(self) -> Optional[float]:
        """Calculate execution time if start_time was set"""
        if self.start_time:
            return (time.time() - self.start_time) * 1000  # Return in milliseconds
        return None

    def start_timer(self):
        """Start timing for performance measurement"""
        self.start_time = time.time()

    def info(
        self,
        message: str,
        platform: Optional[str] = None,
        device_info: Optional[Dict] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs,
    ):
        """Enhanced info logging with automatic enrichment"""
        enriched_data = self._get_enriched_data(
            platform=platform,
            device_info=device_info,
            user_agent=user_agent,
            request_id=request_id,
            **kwargs,
        )

        # Route logs based on platform
        self._route_log("info", message, enriched_data)

    def error(
        self,
        message: str,
        platform: Optional[str] = None,
        device_info: Optional[Dict] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        error: Optional[Exception] = None,
        **kwargs,
    ):
        """Enhanced error logging with automatic enrichment"""
        enriched_data = self._get_enriched_data(
            platform=platform,
            device_info=device_info,
            user_agent=user_agent,
            request_id=request_id,
            error_type=type(error).__name__ if error else None,
            error_message=str(error) if error else None,
            **kwargs,
        )

        # Route logs based on platform
        self._route_log("error", message, enriched_data)

    def warning(
        self,
        message: str,
        platform: Optional[str] = None,
        device_info: Optional[Dict] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs,
    ):
        """Enhanced warning logging with automatic enrichment"""
        enriched_data = self._get_enriched_data(
            platform=platform,
            device_info=device_info,
            user_agent=user_agent,
            request_id=request_id,
            **kwargs,
        )

        # Route logs based on platform
        self._route_log("warning", message, enriched_data)

    def debug(
        self,
        message: str,
        platform: Optional[str] = None,
        device_info: Optional[Dict] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs,
    ):
        """Enhanced debug logging with automatic enrichment"""
        enriched_data = self._get_enriched_data(
            platform=platform,
            device_info=device_info,
            user_agent=user_agent,
            request_id=request_id,
            **kwargs,
        )

        # Route logs based on platform
        self._route_log("debug", message, enriched_data)

    def _route_log(self, level: str, message: str, enriched_data: Dict[str, Any]):
        """Route logs to different handlers based on platform and context"""

        platform_category = enriched_data.get("platform_category", "unknown")
        platform = enriched_data.get("platform", "unknown")
        client_type = enriched_data.get("client_type", "unknown")

        # Get platform-specific configuration
        platform_config = get_platform_config(platform_category)

        # Check if we should log based on sampling rate
        if not should_log_for_platform(platform_category, level):
            return

        # Create platform-specific logger name
        logger_name = f"{self.logger.name}.{platform_category}.{platform}"
        platform_logger = logging.getLogger(logger_name)

        # Add routing tags for log aggregation
        routing_data = {
            "routing": {
                "platform_category": platform_category,
                "platform": platform,
                "client_type": client_type,
                "needs_high_priority": level.lower() in ["error", "critical"]
                or platform_config.get("priority") == "high",
                "mobile_specific": platform_category == "mobile",
                "web_specific": platform_category == "web",
                "separate_handler": platform_config.get("separate_handler", False),
                "include_performance": platform_config.get(
                    "include_performance_metrics", False
                ),
                "include_device_details": platform_config.get(
                    "include_device_details", False
                ),
                "alert_on_errors": platform_config.get("alert_on_errors", False),
                "sample_rate": platform_config.get("sample_rate", 1.0),
            }
        }

        # Conditionally include device details based on platform config
        final_data = {**enriched_data, **routing_data}
        if not platform_config.get("include_device_details", True):
            final_data.pop("device_info", None)

        # Conditionally include performance metrics
        if not platform_config.get("include_performance_metrics", True):
            final_data.pop("execution_time_ms", None)

        # Route to appropriate loggers based on configuration
        if platform_config.get("separate_handler", False):
            # Log to platform-specific logger
            log_method = getattr(platform_logger, level.lower(), platform_logger.info)
            log_method(
                message,
                extra={
                    "custom_dimensions": final_data,
                    "platform_routing": routing_data["routing"],
                },
            )

        # Log to main logger (always, but with different formatting)
        main_log_method = getattr(self.logger, level.lower(), self.logger.info)
        main_log_method(
            f"[{platform.upper()}-{platform_category.upper()}] {message}",
            extra={"custom_dimensions": final_data},
        )

        # Send to error alerts logger if configured
        if level.lower() in ["error", "critical"] and platform_config.get(
            "alert_on_errors", False
        ):
            error_logger = logging.getLogger("error_alerts")
            error_logger.error(
                f"[ALERT] [{platform.upper()}] {message}",
                extra={"custom_dimensions": final_data},
            )

        # Send performance logs to performance logger
        if final_data.get("execution_time_ms") and platform_config.get(
            "include_performance_metrics", False
        ):
            perf_logger = logging.getLogger("performance")
            perf_logger.info(
                f"[PERFORMANCE] [{platform.upper()}] {message}",
                extra={"custom_dimensions": final_data},
            )


def get_enhanced_logger(name: str) -> EnhancedLogger:
    """Factory function to create enhanced logger instances"""
    return EnhancedLogger(name)
