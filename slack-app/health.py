import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Optional

logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health checks"""
    
    def __init__(self, health_checker, *args, **kwargs):
        self.health_checker = health_checker
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/health" or self.path == "/":
            self._handle_health()
        elif self.path == "/ready":
            self._handle_readiness()
        else:
            self._send_response(404, {"error": "Not found"})
    
    def _handle_health(self):
        """Handle health check requests"""
        try:
            status = self.health_checker.get_health()
            code = 200 if status["status"] == "healthy" else 503
            self._send_response(code, status)
        except Exception as e:
            logger.error(f"Health check error: {e}")
            self._send_response(503, {"status": "unhealthy", "error": str(e)})
    
    def _handle_readiness(self):
        """Handle readiness check requests"""
        try:
            status = self.health_checker.get_readiness()
            code = 200 if status["ready"] else 503
            self._send_response(code, status)
        except Exception as e:
            logger.error(f"Readiness check error: {e}")
            self._send_response(503, {"ready": False, "error": str(e)})
    
    def _send_response(self, code: int, data: dict):
        """Send JSON response"""
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.debug(format % args)

class HealthChecker:
    """Health check logic"""
    
    def __init__(self, message_processor=None, rag_client=None):
        self.message_processor = message_processor
        self.rag_client = rag_client
    
    def get_health(self) -> dict:
        """Get application health status"""
        status = {
            "status": "healthy",
            "timestamp": self._get_timestamp(),
            "components": {}
        }
        
        # Check message processor
        if self.message_processor:
            try:
                bot_id = getattr(self.message_processor, 'bot_user_id', None)
                status["components"]["slack"] = {
                    "status": "healthy" if bot_id else "degraded",
                    "bot_id": bot_id
                }
            except Exception as e:
                status["components"]["slack"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                status["status"] = "unhealthy"
        
        # Check RAG system
        if self.rag_client:
            try:
                rag_healthy = self.rag_client.health_check()
                rag_stats = self.rag_client.get_collection_stats()
                status["components"]["rag"] = {
                    "status": "healthy" if rag_healthy else "unhealthy",
                    "stats": rag_stats
                }
                if not rag_healthy:
                    status["status"] = "degraded"  # RAG failure is non-critical
            except Exception as e:
                status["components"]["rag"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                # RAG failure doesn't make the whole service unhealthy
                if status["status"] == "healthy":
                    status["status"] = "degraded"
        
        return status
    
    def get_readiness(self) -> dict:
        """Get application readiness status"""
        ready = True
        components = {}
        
        # Check if message processor is ready
        if self.message_processor:
            try:
                bot_id = getattr(self.message_processor, 'bot_user_id', None)
                components["slack"] = bool(bot_id)
                if not bot_id:
                    ready = False
            except:
                components["slack"] = False
                ready = False
        
        return {
            "ready": ready,
            "timestamp": self._get_timestamp(),
            "components": components
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"

class HealthServer:
    """HTTP server for health checks"""
    
    def __init__(self, port: int, health_checker: HealthChecker):
        self.port = port
        self.health_checker = health_checker
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[Thread] = None
    
    def start(self):
        """Start the health check server"""
        try:
            handler = lambda *args, **kwargs: HealthCheckHandler(self.health_checker, *args, **kwargs)
            self.server = HTTPServer(('0.0.0.0', self.port), handler)
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"Health check server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start health check server: {e}")
            raise
    
    def stop(self):
        """Stop the health check server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Health check server stopped")
