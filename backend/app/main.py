"""
Enterprise Google Meet Sentiment Analysis Bot - Main Application
FastAPI backend with comprehensive API endpoints, middleware, and error handling
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from prometheus_client import make_asgi_app, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import get_settings
from app.core.database import database, engine, metadata
from app.core.redis import redis_client
from app.core.logging import setup_logging
from app.api.v1.api import api_router
from app.core.exceptions import (
    AppException,
    ValidationException,
    AuthenticationException,
    AuthorizationException
)
from app.services.bot_manager import BotManager
from app.services.sentiment_analyzer import SentimentAnalyzer
from app.services.email_service import EmailService

# Initialize settings
settings = get_settings()

# Setup structured logging
logger = setup_logging()

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting metrics"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = REQUEST_LATENCY.start_timer()
        
        try:
            response = await call_next(request)
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()
            
            return response
        finally:
            start_time.stop()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = f"{id(request)}"
        
        # Log request
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            headers=dict(request.headers),
            client_ip=request.client.host if request.client else None
        )
        
        try:
            response = await call_next(request)
            
            # Log response
            logger.info(
                "Request completed",
                request_id=request_id,
                status_code=response.status_code,
                response_headers=dict(response.headers)
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Request failed",
                request_id=request_id,
                error=str(e),
                exc_info=True
            )
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    
    # Startup
    logger.info("Starting up Google Meet Sentiment Bot API...")
    
    try:
        # Initialize database
        if settings.DATABASE_URL:
            await database.connect()
            logger.info("Database connected successfully")
        
        # Initialize Redis
        if settings.REDIS_URL:
            await redis_client.ping()
            logger.info("Redis connected successfully")
        
        # Initialize services
        app.state.bot_manager = BotManager()
        app.state.sentiment_analyzer = SentimentAnalyzer()
        app.state.email_service = EmailService()
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Google Meet Sentiment Bot API...")
    
    try:
        # Cleanup bot manager
        if hasattr(app.state, 'bot_manager'):
            await app.state.bot_manager.cleanup_all()
        
        # Disconnect database
        if database.is_connected:
            await database.disconnect()
            logger.info("Database disconnected")
        
        # Close Redis connection
        if redis_client:
            await redis_client.close()
            logger.info("Redis disconnected")
            
        logger.info("Shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title="Google Meet Sentiment Analysis Bot",
    description="Enterprise-grade automated meeting assistant with real-time sentiment analysis",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

# Security
security = HTTPBearer()

# Add middleware (order matters!)
if settings.TRUSTED_HOSTS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.TRUSTED_HOSTS.split(",")
    )

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(MetricsMiddleware)
app.add_middleware(LoggingMiddleware)


# Exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom application exceptions"""
    logger.error(
        "Application exception",
        error=str(exc),
        error_code=exc.error_code,
        status_code=exc.status_code,
        url=str(request.url)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": str(exc),
                "details": exc.details
            }
        }
    )


@app.exception_handler(ValidationException)
async def validation_exception_handler(request: Request, exc: ValidationException):
    """Handle validation exceptions"""
    logger.warning(
        "Validation error",
        error=str(exc),
        validation_errors=exc.details,
        url=str(request.url)
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": exc.details
            }
        }
    )


@app.exception_handler(AuthenticationException)
async def auth_exception_handler(request: Request, exc: AuthenticationException):
    """Handle authentication exceptions"""
    logger.warning(
        "Authentication error",
        error=str(exc),
        url=str(request.url)
    )
    
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": "AUTHENTICATION_ERROR",
                "message": "Authentication required"
            }
        }
    )


@app.exception_handler(AuthorizationException)
async def authorization_exception_handler(request: Request, exc: AuthorizationException):
    """Handle authorization exceptions"""
    logger.warning(
        "Authorization error",
        error=str(exc),
        url=str(request.url)
    )
    
    return JSONResponse(
        status_code=403,
        content={
            "error": {
                "code": "AUTHORIZATION_ERROR",
                "message": "Insufficient permissions"
            }
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(
        "Unexpected error",
        error=str(exc),
        error_type=type(exc).__name__,
        url=str(request.url),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    )


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": logger.info("Health check requested")
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with service status"""
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "services": {}
    }
    
    # Check database
    try:
        if database.is_connected:
            health_status["services"]["database"] = "healthy"
        else:
            health_status["services"]["database"] = "disconnected"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        await redis_client.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check bot manager
    try:
        if hasattr(app.state, 'bot_manager'):
            bot_count = len(app.state.bot_manager.active_bots)
            health_status["services"]["bot_manager"] = f"healthy ({bot_count} active bots)"
        else:
            health_status["services"]["bot_manager"] = "not initialized"
    except Exception as e:
        health_status["services"]["bot_manager"] = f"error: {str(e)}"
    
    return health_status


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return PlainTextResponse(generate_latest())


# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Google Meet Sentiment Analysis Bot API",
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else "Documentation not available in production",
        "health": "/health"
    }


# WebSocket endpoint for real-time updates
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket, session_id: str):
    """WebSocket endpoint for real-time session updates"""
    await websocket.accept()
    
    try:
        logger.info(f"WebSocket connection established for session: {session_id}")
        
        # Add client to session
        if hasattr(app.state, 'bot_manager'):
            await app.state.bot_manager.add_websocket_client(session_id, websocket)
        
        # Keep connection alive
        while True:
            try:
                # Wait for client messages or send heartbeat
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_text('{"type": "heartbeat"}')
            
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {str(e)}")
    
    finally:
        if hasattr(app.state, 'bot_manager'):
            await app.state.bot_manager.remove_websocket_client(session_id, websocket)
        
        logger.info(f"WebSocket connection closed for session: {session_id}")


# Dependency injection helpers
def get_bot_manager() -> BotManager:
    """Get bot manager instance"""
    return app.state.bot_manager


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get sentiment analyzer instance"""
    return app.state.sentiment_analyzer


def get_email_service() -> EmailService:
    """Get email service instance"""
    return app.state.email_service


if __name__ == "__main__":
    # Run with uvicorn for development
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
        access_log=True
    )