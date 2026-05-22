"""
HTTP Proxy Server for Token Telemetry.

Intercepts API calls from Vibe CLI, logs telemetry data, forwards requests to
Mistral API, and returns responses. Non-blocking and handles errors gracefully.
"""

import json
import logging
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from token_telemetry.config import Config
from token_telemetry.cost_calculator import CostCalculator, calculate_cost
from token_telemetry.database import Database, get_database
from token_telemetry.models import CallRecord

logger = logging.getLogger(__name__)


# Default headers to forward to Mistral API
FORWARD_HEADERS = [
    "Authorization",
    "Content-Type",
    "Accept",
    "User-Agent",
    "X-Request-ID",
]

# Headers we extract for telemetry
TELEMETRY_HEADERS = [
    "X-Telemetry-Model",
    "X-Telemetry-Origin",
    "X-Model",
    "X-Origin",
]


class TelemetryHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler that intercepts API calls and logs telemetry.
    """
    
    # Class-level storage for shared state
    database: Optional[Database] = None
    cost_calculator: Optional[CostCalculator] = None
    mistral_base_url: str = "https://api.mistral.ai"
    track_endpoints: Optional[List[str]] = None
    ignore_endpoints: Optional[List[str]] = None
    
    def __init__(
        self,
        *args: Any,
        database: Optional[Database] = None,
        cost_calculator: Optional[CostCalculator] = None,
        mistral_base_url: str = "https://api.mistral.ai",
        track_endpoints: Optional[List[str]] = None,
        ignore_endpoints: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        self.database = database or self.__class__.database
        self.cost_calculator = cost_calculator or self.__class__.cost_calculator
        self.mistral_base_url = mistral_base_url or self.__class__.mistral_base_url
        self.track_endpoints = track_endpoints or self.__class__.track_endpoints
        self.ignore_endpoints = ignore_endpoints or self.__class__.ignore_endpoints
        super().__init__(*args, **kwargs)
    
    def log_message(self, format: str, *args: Any) -> None:
        """Override default logging to use our logger."""
        logger.info("%s - - %s" % (self.address_string(), format % args))
    
    def _extract_model(self, post_data: Optional[bytes] = None) -> str:
        """
        Extract the model name from the request.
        
        Checks (in order):
        1. Custom headers
        2. Request body (JSON) for 'model' field
        3. URL path for model name patterns
        
        Args:
            post_data: Optional request body data (bytes)
            
        Returns:
            Model name or 'unknown'
        """
        # Check custom headers first
        for header in TELEMETRY_HEADERS:
            if header in self.headers:
                return self.headers[header]
        
        # Try to extract from request body (JSON)
        if post_data:
            try:
                body_json = json.loads(post_data.decode('utf-8'))
                if isinstance(body_json, dict):
                    model = body_json.get('model')
                    if model:
                        return model
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                # If body is not JSON or can't be decoded, continue to other methods
                pass
        
        # Try to extract from path
        path = self.path.lower()
        for model in ["mistral-tiny", "mistral-small", "mistral-medium", "mistral-large", "codestral"]:
            if model in path:
                return model
        
        return "unknown"
    
    def _extract_origin(self) -> str:
        """
        Extract the origin from the request.
        
        Checks headers for origin information.
        
        Returns:
            Origin (user, agent, sub-agent) or 'unknown'
        """
        # Check custom headers
        origin_header = self.headers.get("X-Telemetry-Origin") or self.headers.get("X-Origin")
        if origin_header:
            return origin_header.lower()
        
        # Default to user
        return "user"
    
    def _should_track_endpoint(self, path: str) -> bool:
        """
        Determine if an endpoint should be tracked for telemetry.
        
        Args:
            path: The request path
            
        Returns:
            True if the endpoint should be tracked, False otherwise
        """
        # Default to tracking all endpoints
        if self.track_endpoints is None and self.ignore_endpoints is None:
            return True
        
        # If we have a whitelist (track_endpoints), only track if path matches
        if self.track_endpoints:
            for pattern in self.track_endpoints:
                if pattern in path:
                    return True
            return False
        
        # If we have a blacklist (ignore_endpoints), track unless path matches
        if self.ignore_endpoints:
            for pattern in self.ignore_endpoints:
                if pattern in path:
                    return False
            return True
        
        return True
    
    def _extract_request_tokens(self) -> int:
        """
        Extract request token count from headers or body.
        
        Returns:
            Number of request tokens or 0
        """
        # Check if token count is in headers
        token_header = self.headers.get("X-Telemetry-Request-Tokens")
        if token_header:
            try:
                return int(token_header)
            except ValueError:
                pass
        
        # For Mistral API, we might need to parse the body
        # But this requires reading the body which we need to forward
        # So we'll leave this to be calculated from the response
        return 0
    
    def _forward_request(self, request_data: Dict[str, Any]) -> requests.Response:
        """
        Forward the request to the Mistral API.
        
        Args:
            request_data: Dictionary containing method, url, headers, data
            
        Returns:
            Response from the Mistral API
        """
        try:
            response = requests.request(
                method=request_data["method"],
                url=request_data["url"],
                headers=request_data["headers"],
                data=request_data["data"],
                timeout=30,  # 30 second timeout
            )
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to forward request: {e}")
            raise
    
    def _log_telemetry(
        self,
        request_data: Dict[str, Any],
        response: requests.Response,
        processing_time: float,
    ) -> CallRecord:
        """
        Log telemetry data for this API call.
        
        Args:
            request_data: Request information
            response: Response from Mistral API
            processing_time: Time taken for the request
            
        Returns:
            CallRecord with the logged data
        """
        # Extract response data
        status_code = response.status_code
        
        # Try to extract token counts from response
        request_tokens = 0
        response_tokens = 0
        
        try:
            response_json = response.json()
            usage = response_json.get("usage", {})
            request_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
            response_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
        except (json.JSONDecodeError, KeyError, AttributeError, ValueError):
            logger.debug("Could not extract token counts from response")
        
        # Extract model and origin
        model = request_data.get("model", "unknown")
        origin = request_data.get("origin", "user")
        
        # Calculate cost
        cost = 0.0
        if self.cost_calculator:
            cost = self.cost_calculator.calculate_cost(
                model=model,
                input_tokens=request_tokens,
                output_tokens=response_tokens,
            )
        
        # Create call record
        record = CallRecord(
            timestamp=datetime.utcnow().isoformat(),
            model=model,
            endpoint=request_data["url"],
            origin=origin,
            request_tokens=request_tokens,
            response_tokens=response_tokens,
            processing_time=processing_time,
            status_code=status_code,
            cost=cost,
        )
        
        # Store in database
        if self.database:
            try:
                self.database.insert_record(record)
                logger.debug(f"Logged telemetry: {record.model}, {record.total_tokens()} tokens, ${record.cost:.6f}")
            except Exception as e:
                logger.error(f"Failed to log telemetry: {e}")
                # Non-blocking: continue even if logging fails
        
        return record
    
    def _build_response(self, response: requests.Response) -> None:
        """
        Build and send the HTTP response to the client.
        
        Args:
            response: Response from Mistral API
        """
        # Send response status code
        self.send_response(response.status_code)
        
        # Copy response headers
        for header, value in response.headers.items():
            if header not in ["Content-Length", "Transfer-Encoding", "Connection"]:
                self.send_header(header, value)
        
        self.end_headers()
        
        # Send response body
        try:
            self.wfile.write(response.content)
        except Exception as e:
            logger.error(f"Failed to send response body: {e}")
    
    def do_POST(self) -> None:
        """Handle POST requests (main API call method)."""
        start_time = time.time()
        
        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b""
            
            # Check if this endpoint should be tracked
            if not self._should_track_endpoint(self.path):
                # Just forward the request without logging telemetry
                request_url = f"{self.mistral_base_url}{self.path}"
                forward_headers = {}
                for header in FORWARD_HEADERS:
                    if header in self.headers:
                        forward_headers[header] = self.headers[header]
                
                request_data = {
                    "method": "POST",
                    "url": request_url,
                    "headers": forward_headers,
                    "data": post_data,
                    "model": "ignored",
                    "origin": "ignored",
                }
                
                response = self._forward_request(request_data)
                self._build_response(response)
                return
            
            # Extract model and origin
            model = self._extract_model(post_data=post_data)
            origin = self._extract_origin()
            
            # Build request data for forwarding
            request_url = f"{self.mistral_base_url}{self.path}"
            
            # Filter headers to forward
            forward_headers = {}
            for header in FORWARD_HEADERS:
                if header in self.headers:
                    forward_headers[header] = self.headers[header]
            
            # Add our own headers for tracking
            forward_headers["X-Telemetry-Model"] = model
            forward_headers["X-Telemetry-Origin"] = origin
            
            request_data = {
                "method": "POST",
                "url": request_url,
                "headers": forward_headers,
                "data": post_data,
                "model": model,
                "origin": origin,
            }
            
            # Forward request
            logger.debug(f"Forwarding request to {request_url}")
            response = self._forward_request(request_data)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log telemetry
            self._log_telemetry(request_data, response, processing_time)
            
            # Send response back to client
            self._build_response(response)
            
        except Exception as e:
            logger.error(f"Error handling POST request: {e}")
            # Return 500 error if something went wrong
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_response = {
                "error": "Internal server error",
                "message": str(e),
            }
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_GET(self) -> None:
        """Handle GET requests."""
        start_time = time.time()
        
        try:
            # Check if this endpoint should be tracked
            if not self._should_track_endpoint(self.path):
                # Just forward the request without logging telemetry
                request_url = f"{self.mistral_base_url}{self.path}"
                forward_headers = {}
                for header in FORWARD_HEADERS:
                    if header in self.headers:
                        forward_headers[header] = self.headers[header]
                
                request_data = {
                    "method": "GET",
                    "url": request_url,
                    "headers": forward_headers,
                    "data": None,
                    "model": "ignored",
                    "origin": "ignored",
                }
                
                response = self._forward_request(request_data)
                self._build_response(response)
                return
            
            # Build request data for forwarding
            request_url = f"{self.mistral_base_url}{self.path}"
            
            # Filter headers to forward
            forward_headers = {}
            for header in FORWARD_HEADERS:
                if header in self.headers:
                    forward_headers[header] = self.headers[header]
            
            # Extract model and origin
            model = self._extract_model()
            origin = self._extract_origin()
            
            forward_headers["X-Telemetry-Model"] = model
            forward_headers["X-Telemetry-Origin"] = origin
            
            request_data = {
                "method": "GET",
                "url": request_url,
                "headers": forward_headers,
                "data": None,
                "model": model,
                "origin": origin,
            }
            
            # Forward request
            logger.debug(f"Forwarding GET request to {request_url}")
            response = self._forward_request(request_data)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log telemetry
            self._log_telemetry(request_data, response, processing_time)
            
            # Send response back to client
            self._build_response(response)
            
        except Exception as e:
            logger.error(f"Error handling GET request: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_response = {
                "error": "Internal server error",
                "message": str(e),
            }
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_PUT(self) -> None:
        """Handle PUT requests."""
        self.do_POST()  # Treat PUT same as POST for now
    
    def do_DELETE(self) -> None:
        """Handle DELETE requests."""
        self.do_GET()  # Treat DELETE same as GET for now
    
    def do_PATCH(self) -> None:
        """Handle PATCH requests."""
        self.do_POST()  # Treat PATCH same as POST for now


class ProxyServer:
    """
    HTTP Proxy Server for Token Telemetry.
    
    Wraps the standard HTTPServer and manages the proxy lifecycle.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        mistral_base_url: str = "https://api.mistral.ai",
        db_path: str = "telemetry.db",
        pricing_config: Optional[Dict[str, Dict[str, float]]] = None,
        track_endpoints: Optional[List[str]] = None,
        ignore_endpoints: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize the proxy server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
            mistral_base_url: Base URL for Mistral API
            db_path: Path to SQLite database
            pricing_config: Pricing configuration for cost calculator
            track_endpoints: List of endpoint patterns to track (whitelist)
            ignore_endpoints: List of endpoint patterns to ignore (blacklist)
        """
        self.host = host
        self.port = port
        self.mistral_base_url = mistral_base_url
        self.db_path = db_path
        self.pricing_config = pricing_config
        self.track_endpoints = track_endpoints
        self.ignore_endpoints = ignore_endpoints
        
        # Create database instance
        self.database = Database(db_path)
        
        # Create cost calculator
        self.cost_calculator = CostCalculator(pricing_config)
        
        # Create server
        self.server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
    
    def start(self) -> None:
        """Start the proxy server."""
        # Configure handler class with our instances
        TelemetryHandler.database = self.database
        TelemetryHandler.cost_calculator = self.cost_calculator
        TelemetryHandler.mistral_base_url = self.mistral_base_url
        TelemetryHandler.track_endpoints = self.track_endpoints
        TelemetryHandler.ignore_endpoints = self.ignore_endpoints
        
        # Create server
        self.server = HTTPServer((self.host, self.port), TelemetryHandler)
        
        logger.info(f"Starting proxy server on {self.host}:{self.port}")
        logger.info(f"Forwarding to: {self.mistral_base_url}")
        logger.info(f"Database: {self.db_path}")
        logger.info(f"Press Ctrl+C to stop")
        
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.stop()
    
    def start_in_thread(self) -> None:
        """Start the proxy server in a background thread."""
        # Configure handler class with our instances
        TelemetryHandler.database = self.database
        TelemetryHandler.cost_calculator = self.cost_calculator
        TelemetryHandler.mistral_base_url = self.mistral_base_url
        TelemetryHandler.track_endpoints = self.track_endpoints
        TelemetryHandler.ignore_endpoints = self.ignore_endpoints
        
        # Create server
        self.server = HTTPServer((self.host, self.port), TelemetryHandler)
        
        # Start in thread
        self._server_thread = threading.Thread(target=self.server.serve_forever)
        self._server_thread.daemon = True
        self._server_thread.start()
        
        logger.info(f"Proxy server started in background on {self.host}:{self.port}")
    
    def stop(self) -> None:
        """Stop the proxy server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            logger.info("Proxy server stopped")
        
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=5)
    
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self.server is not None


def main() -> None:
    """Main entry point for running the proxy server from command line."""
    import argparse
    import sys
    
    from token_telemetry.config import load_config
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Token Telemetry Proxy Server - Intercepts API calls and logs telemetry"
    )
    parser.add_argument(
        "-H", "--host",
        type=str,
        default=None,
        help="Host to run the proxy server on (default: from config)",
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=None,
        help="Port to run the proxy server on (default: from config)",
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="Path to configuration file",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
    
    # Load configuration
    config = load_config(config_path=args.config)
    
    # Override with command-line arguments
    if args.host:
        config.proxy.host = args.host
    if args.port:
        config.proxy.port = args.port
    
    # Create and start proxy server
    server = ProxyServer(
        host=config.proxy.host,
        port=config.proxy.port,
        mistral_base_url=config.mistral.base_url,
        db_path=config.database.path,
        pricing_config=config.pricing,
        track_endpoints=config.proxy.track_endpoints,
        ignore_endpoints=config.proxy.ignore_endpoints,
    )
    
    server.start()


if __name__ == "__main__":
    main()
