# Enhanced Logging System for WAVE API

## Overview

The enhanced logging system provides automatic log enrichment and platform-based routing for the WAVE API, specifically implemented in the `get_events_preview` endpoint.

## Features

### 🚀 Automatic Log Enrichment

-   **Request Tracking**: Unique request IDs for tracing across services
-   **Performance Metrics**: Automatic timing measurement
-   **Device Intelligence**: Detailed device and client type detection
-   **OpenTelemetry Integration**: Automatic trace and span correlation
-   **Client Geography**: IP-based location detection (when available)

### 📱 Platform-Based Routing

Logs are automatically routed differently based on platform:

| Platform    | Priority | Separate Handler | Performance Metrics | Device Details | Alert on Errors | Sample Rate |
| ----------- | -------- | ---------------- | ------------------- | -------------- | --------------- | ----------- |
| **Mobile**  | High     | ✅               | ✅                  | ✅             | ✅              | 100%        |
| **Web**     | Medium   | ✅               | ✅                  | ❌             | ✅              | 80%         |
| **Desktop** | Low      | ❌               | ❌                  | ❌             | ❌              | 50%         |
| **Unknown** | Medium   | ❌               | ❌                  | ✅             | ✅              | 100%        |

### 🎯 Smart Client Detection

The system automatically detects and categorizes clients:

-   **Mobile Apps**: Native iOS/Android applications
-   **Mobile Browsers**: Mobile web browsers
-   **Desktop Browsers**: Chrome, Firefox, Safari, Edge
-   **API Clients**: Postman, curl, Python requests, etc.

## Implementation

### Enhanced Logger Usage

```python
from apiManager.utilities.enhanced_logger import get_enhanced_logger

# Initialize enhanced logger
enhanced_logger = get_enhanced_logger(__name__)

# Start performance timing
enhanced_logger.start_timer()

# Log with automatic enrichment
enhanced_logger.info(
    "Events preview request initiated",
    platform=platform,
    device_info=device_info,
    user_agent=user_agent_str,
    request_id=request_id,
    # Additional context
    client_ip=client_ip,
    referer=referer,
    endpoint="get_events_preview",
    operation="fetch_preview_events",
)
```

### Platform Configuration

Configure platform-specific behavior in `logging_config.py`:

```python
PLATFORM_ROUTING_CONFIG = {
    "mobile": {
        "priority": "high",
        "separate_handler": True,
        "include_performance_metrics": True,
        "include_device_details": True,
        "alert_on_errors": True,
        "sample_rate": 1.0,
    },
    # ... other platforms
}
```

## Log Structure

### Standard Log Entry

```json
{
	"timestamp": "2024-01-15T10:30:45.123Z",
	"request_id": "550e8400-e29b-41d4-a716-446655440000",
	"platform": "ios",
	"platform_category": "mobile",
	"trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
	"span_id": "00f067aa0ba902b7",
	"device_info": {
		"device_type": "iOS",
		"device_info": "iOS - Safari 17.1 - iOS 17.1 - iPhone Apple iPhone 15"
	},
	"client_type": "mobile_app",
	"execution_time_ms": 245.7,
	"client_ip": "192.168.1.100",
	"referer": "https://app.wave.com/explore",
	"endpoint": "get_events_preview",
	"operation": "fetch_preview_events"
}
```

### Platform Routing Tags

```json
{
	"routing": {
		"platform_category": "mobile",
		"platform": "ios",
		"client_type": "mobile_app",
		"needs_high_priority": true,
		"mobile_specific": true,
		"web_specific": false,
		"separate_handler": true,
		"include_performance": true,
		"alert_on_errors": true,
		"sample_rate": 1.0
	}
}
```

## Enhanced get_events_preview Function

The enhanced implementation includes:

### 🔄 Request Lifecycle Logging

-   **Initiation**: Request start with full context
-   **Database Operations**: Query timing and results
-   **Individual Event Processing**: Per-event success/failure tracking
-   **Response Generation**: Final metrics and timing
-   **Error Handling**: Comprehensive error context

### ⚡ Performance Monitoring

-   **Database Query Timing**: Track database operation performance
-   **Event Processing Time**: Monitor serialization overhead
-   **End-to-End Timing**: Complete request lifecycle timing

### 🛡️ Error Handling

-   **Granular Error Logging**: Individual event processing failures
-   **Context Preservation**: Full request context in error logs
-   **Platform-Specific Alerts**: Configurable error notifications
-   **Request ID Correlation**: Easy error tracking across systems

### 📊 Business Metrics

-   **Event Statistics**: Count, types, locations, photos
-   **Success Rates**: Processing success/failure ratios
-   **Platform Usage**: Platform-specific usage patterns

## Log Outputs by Platform

### Mobile Logs (iOS/Android)

```
[2024-01-15 10:30:45] INFO [MOBILE:ios] [mobile_app] [550e8400] Events preview request initiated
[2024-01-15 10:30:45] DEBUG [MOBILE:ios] [mobile_app] [550e8400] Starting database query for preview events
[2024-01-15 10:30:45] DEBUG [MOBILE:ios] [mobile_app] [550e8400] Processed event for preview
[2024-01-15 10:30:45] INFO [MOBILE:ios] [mobile_app] [550e8400] Successfully fetched and processed preview events
[2024-01-15 10:30:45] INFO [PERF:ios] [245ms] [550e8400] Events preview request initiated
```

### Web Logs

```
[2024-01-15 10:30:45] INFO [WEB:web] [550e8400] Events preview request initiated
[2024-01-15 10:30:45] INFO [WEB:web] [550e8400] Successfully fetched and processed preview events
```

### Error Logs with Alerts

```
[2024-01-15 10:30:45] ERROR [IOS-MOBILE] Failed to fetch events preview
[2024-01-15 10:30:45] ERROR [ALERT] [IOS] Failed to fetch events preview
```

## Configuration

### Environment Variables

```bash
# Enable enhanced logging
ENVIRONMENT=production

# OpenTelemetry configuration
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-us-central1.grafana.net/otlp
GRAFANA_API_KEY=glc_your_token_here
OTEL_ENVIRONMENT=production
```

### Setup Enhanced Logging

```python
from apiManager.utilities.logging_config import setup_enhanced_logging

# Apply enhanced logging configuration
setup_enhanced_logging()
```

## Benefits

### 🔍 **Improved Debugging**

-   Unique request IDs for tracing issues across logs
-   Complete request context preserved in error logs
-   Platform-specific log formatting for easier parsing

### 📈 **Better Monitoring**

-   Performance metrics automatically captured
-   Platform usage patterns clearly visible
-   Business metrics integrated into logs

### ⚡ **Optimized Performance**

-   Sampling rates reduce log volume for low-priority platforms
-   Conditional enrichment saves processing overhead
-   Platform-specific routing prevents log noise

### 🚨 **Enhanced Alerting**

-   Platform-aware error notifications
-   High-priority routing for mobile issues
-   Performance threshold monitoring

## Future Enhancements

-   [ ] Add metrics export to Prometheus
-   [ ] Implement log-based alerting rules
-   [ ] Add custom dashboard templates
-   [ ] Support for A/B testing log tagging
-   [ ] Integration with business intelligence tools
