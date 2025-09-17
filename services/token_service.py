"""
Token Service for secure sharing token management.
Handles token generation, validation, consumption, and cleanup.
Optimized for Azure App Service with external SQL database.
"""

import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from flask import current_app
from sqlalchemy.exc import IntegrityError, OperationalError, TimeoutError
from sqlalchemy import text

# Configure logging for Azure App Service
logger = logging.getLogger(__name__)


class TokenGenerationError(Exception):
    """Raised when token generation fails"""
    pass


class TokenValidationError(Exception):
    """Raised when token validation fails"""
    pass


class TokenService:
    """
    Service class for managing sharing tokens.
    Designed for Azure App Service with external SQL database.
    """
    
    # Configuration values optimized for Azure/production
    DEFAULT_EXPIRY_HOURS = 24
    DEFAULT_MAX_USES = 1
    MAX_GENERATION_ATTEMPTS = 3  # Reduced for faster response in cloud
    TOKEN_LENGTH = 32
    
    # Azure-specific timeouts and retry settings
    DB_TIMEOUT_SECONDS = 30
    MAX_DB_RETRIES = 2
    CLEANUP_BATCH_SIZE = 50  # Smaller batches for Azure SQL
    
    @classmethod
    def generate_token(
        cls,
        project_id: int,
        created_by: int,
        role: str = 'viewer',
        expires_hours: int = None,
        max_uses: int = None,
        custom_token: str = None
    ):
        """
        Generate a new sharing token with specified parameters.
        Optimized for Azure App Service with connection retry logic.
        
        Args:
            project_id: ID of the project to share
            created_by: ID of the user creating the token
            role: Role to assign to users who use this token
            expires_hours: Hours until token expires (default: 24)
            max_uses: Maximum number of times token can be used (default: 1)
            custom_token: Custom token string (for testing, optional)
            
        Returns:
            SharingToken: The created token object
            
        Raises:
            TokenGenerationError: If token generation fails
        """
        from app import db, SharingToken, SharingActivityLog
        
        if expires_hours is None:
            expires_hours = cls.DEFAULT_EXPIRY_HOURS
        if max_uses is None:
            max_uses = cls.DEFAULT_MAX_USES
            
        # Validate inputs
        if expires_hours <= 0:
            raise TokenGenerationError("Expiry hours must be positive")
        if max_uses <= 0:
            raise TokenGenerationError("Max uses must be positive")
        if role not in ['viewer', 'editor', 'admin']:
            raise TokenGenerationError(f"Invalid role: {role}")
            
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        # Generate unique token with retry logic for Azure SQL
        for attempt in range(cls.MAX_GENERATION_ATTEMPTS):
            try:
                token_string = custom_token or cls._generate_secure_token()
                
                sharing_token = SharingToken(
                    token=token_string,
                    project_id=project_id,
                    created_by=created_by,
                    role=role,
                    expires_at=expires_at,
                    max_uses=max_uses,
                    current_uses=0,
                    is_active=True
                )
                
                db.session.add(sharing_token)
                db.session.flush()  # Get the ID without committing
                
                # Log token generation
                SharingActivityLog.log_activity(
                    project_id=project_id,
                    user_id=created_by,
                    action='token_generated',
                    details=f"Token generated with role '{role}', expires in {expires_hours} hours, max uses: {max_uses}"
                )
                
                db.session.commit()
                logger.info(f"Token generated successfully for project {project_id}")
                return sharing_token
                
            except IntegrityError:
                db.session.rollback()
                logger.warning(f"Token collision on attempt {attempt + 1}")
                if attempt == cls.MAX_GENERATION_ATTEMPTS - 1:
                    raise TokenGenerationError("Failed to generate unique token after multiple attempts")
                continue
            except (OperationalError, TimeoutError) as e:
                db.session.rollback()
                logger.error(f"Database error during token generation: {str(e)}")
                if attempt == cls.MAX_GENERATION_ATTEMPTS - 1:
                    raise TokenGenerationError(f"Database connection failed: {str(e)}")
                continue
            except Exception as e:
                db.session.rollback()
                logger.error(f"Unexpected error during token generation: {str(e)}")
                raise TokenGenerationError(f"Token generation failed: {str(e)}")
        
        raise TokenGenerationError("Token generation failed")
    
    @classmethod
    def validate_token(cls, token_string: str) -> Dict[str, Any]:
        """
        Validate a sharing token and return its details.
        
        Args:
            token_string: The token string to validate
            
        Returns:
            Dict containing token validation results and details
            
        Raises:
            TokenValidationError: If token validation fails
        """
        from app import SharingToken
        
        if not token_string:
            raise TokenValidationError("Token string is required")
            
        token = SharingToken.query.filter_by(token=token_string).first()
        
        if not token:
            raise TokenValidationError("Token not found")
            
        validation_result = {
            'token': token,
            'is_valid': False,
            'errors': [],
            'project_id': token.project_id,
            'role': token.role,
            'created_by': token.created_by,
            'expires_at': token.expires_at,
            'max_uses': token.max_uses,
            'current_uses': token.current_uses
        }
        
        # Check if token is active
        if not token.is_active:
            validation_result['errors'].append("Token is inactive")
            
        # Check if token has expired
        if token.expires_at <= datetime.utcnow():
            validation_result['errors'].append("Token has expired")
            
        # Check if token has reached max uses
        if token.current_uses >= token.max_uses:
            validation_result['errors'].append("Token has reached maximum uses")
            
        # Token is valid if no errors
        validation_result['is_valid'] = len(validation_result['errors']) == 0
        
        return validation_result
    
    @classmethod
    def consume_token(
        cls,
        token_string: str,
        user_id: int,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """
        Consume a sharing token (increment usage count).
        
        Args:
            token_string: The token string to consume
            user_id: ID of the user consuming the token
            ip_address: IP address of the user (for logging)
            user_agent: User agent string (for logging)
            
        Returns:
            Dict containing consumption results
            
        Raises:
            TokenValidationError: If token cannot be consumed
        """
        from app import db, SharingActivityLog
        
        validation_result = cls.validate_token(token_string)
        
        if not validation_result['is_valid']:
            raise TokenValidationError(f"Cannot consume invalid token: {', '.join(validation_result['errors'])}")
            
        token = validation_result['token']
        
        try:
            # Increment usage count
            token.current_uses += 1
            
            # Deactivate token if max uses reached
            if token.current_uses >= token.max_uses:
                token.is_active = False
                
            # Log token usage
            SharingActivityLog.log_activity(
                project_id=token.project_id,
                user_id=user_id,
                action='token_used',
                details=f"Token used by user {user_id}, usage {token.current_uses}/{token.max_uses}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.session.commit()
            
            return {
                'success': True,
                'token': token,
                'project_id': token.project_id,
                'role': token.role,
                'remaining_uses': token.max_uses - token.current_uses,
                'is_exhausted': token.current_uses >= token.max_uses
            }
            
        except Exception as e:
            db.session.rollback()
            raise TokenValidationError(f"Failed to consume token: {str(e)}")
    
    @staticmethod
    def _generate_secure_token() -> str:
        """
        Generate a cryptographically secure token.
        
        Returns:
            str: Secure token string
        """
        return secrets.token_urlsafe(TokenService.TOKEN_LENGTH)


class TokenCleanupService:
    """
    Service for automated token cleanup.
    Optimized for Azure App Service with connection pooling and timeout handling.
    """
    
    # Azure-optimized settings
    DEFAULT_BATCH_SIZE = 25  # Smaller for Azure SQL
    DEFAULT_MAX_BATCHES = 5  # Limit processing time
    CLEANUP_TIMEOUT_SECONDS = 60  # Maximum cleanup time
    
    @classmethod
    def run_cleanup(cls, batch_size: int = None, max_batches: int = None) -> Dict[str, int]:
        """
        Run token cleanup with batching optimized for Azure SQL.
        
        Args:
            batch_size: Number of tokens to process per batch (default: 25)
            max_batches: Maximum number of batches to process (default: 5)
            
        Returns:
            Dict containing cleanup statistics
        """
        from services.token_service import TokenService
        
        if batch_size is None:
            batch_size = cls.DEFAULT_BATCH_SIZE
        if max_batches is None:
            max_batches = cls.DEFAULT_MAX_BATCHES
            
        total_cleaned = 0
        batches_processed = 0
        start_time = datetime.utcnow()
        
        logger.info(f"Starting token cleanup with batch_size={batch_size}, max_batches={max_batches}")
        
        for batch in range(max_batches):
            # Check timeout to prevent long-running operations in Azure
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > cls.CLEANUP_TIMEOUT_SECONDS:
                logger.warning(f"Cleanup timeout reached after {elapsed} seconds")
                break
                
            try:
                cleaned_in_batch = TokenService.cleanup_expired_tokens(batch_size)
                total_cleaned += cleaned_in_batch
                batches_processed += 1
                
                logger.debug(f"Batch {batch + 1}: cleaned {cleaned_in_batch} tokens")
                
                # Stop if no more tokens to clean
                if cleaned_in_batch == 0:
                    break
                    
            except Exception as e:
                logger.error(f"Error in cleanup batch {batch + 1}: {str(e)}")
                break
        
        result = {
            'total_cleaned': total_cleaned,
            'batches_processed': batches_processed,
            'batch_size': batch_size,
            'elapsed_seconds': (datetime.utcnow() - start_time).total_seconds()
        }
        
        logger.info(f"Token cleanup completed: {result}")
        return result