"""
Data Models for Token Telemetry System

Defines the data structures used throughout the telemetry system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CallRecord:
    """
    Represents a single API call telemetry record.
    
    Attributes:
        timestamp: ISO 8601 formatted timestamp
        model: Name of the model used
        endpoint: API endpoint URL
        origin: Call initiator (user, agent, sub-agent)
        request_tokens: Number of tokens in the request
        response_tokens: Number of tokens in the response
        processing_time: Time taken to process the request (seconds)
        status_code: HTTP status code
        cost: Calculated cost for the call (USD)
    """
    timestamp: str
    model: str
    endpoint: str
    origin: str
    request_tokens: int
    response_tokens: int
    processing_time: float
    status_code: int
    cost: float
    
    def total_tokens(self) -> int:
        """Calculate total tokens (request + response)."""
        return self.request_tokens + self.response_tokens
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp,
            "model": self.model,
            "endpoint": self.endpoint,
            "origin": self.origin,
            "request_tokens": self.request_tokens,
            "response_tokens": self.response_tokens,
            "processing_time": self.processing_time,
            "status_code": self.status_code,
            "cost": self.cost,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CallRecord":
        """Create CallRecord from dictionary."""
        return cls(
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            model=data.get("model", ""),
            endpoint=data.get("endpoint", ""),
            origin=data.get("origin", "unknown"),
            request_tokens=data.get("request_tokens", 0),
            response_tokens=data.get("response_tokens", 0),
            processing_time=data.get("processing_time", 0.0),
            status_code=data.get("status_code", 0),
            cost=data.get("cost", 0.0),
        )


@dataclass
class SummaryStats:
    """
    Aggregated statistics for reporting.
    
    Attributes:
        total_calls: Total number of API calls
        total_request_tokens: Sum of all request tokens
        total_response_tokens: Sum of all response tokens
        total_cost: Sum of all costs
        by_model: Statistics grouped by model
        by_origin: Statistics grouped by origin
    """
    total_calls: int = 0
    total_request_tokens: int = 0
    total_response_tokens: int = 0
    total_cost: float = 0.0
    by_model: dict = field(default_factory=dict)
    by_origin: dict = field(default_factory=dict)
    
    @property
    def total_tokens(self) -> int:
        """Calculate total tokens across all calls."""
        return self.total_request_tokens + self.total_response_tokens
