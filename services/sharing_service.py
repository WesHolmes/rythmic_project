"""
Sharing Service for Project Collaboration

This module provides secure sharing functionality for projects including:
- Link generation with secure tokens
- Email invitations with templates
- Token processing for invitation acceptance
- Activity logging for audit trails
"""

import os
import secrets
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, Tuple
from flask import current_app, url_for, request, render_template

# Configure logging for Azure App Service
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SharingServiceError(Exception):
    """Base exception for sharing service errors"""
    pass


class EmailDeliveryError(SharingServiceError):
    """Exception raised when email delivery fails"""
    pass


class InvalidTokenError(SharingServiceError):
    """Exception raised when sharing token is invalid"""
    pass


class SharingService:
    """
    Service class for handling project sharing operations including
    link generation, email invitations, and token processing.
    """
    
    def __init__(self):
        # Email configuration priority: SendGrid > Azure Communication Services > SMTP
        self.sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        self.use_sendgrid = self.sendgrid_api_key is not None
        
        self.use_azure_communication = os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING') is not None
        
        if self.use_sendgrid:
            self.from_email = os.environ.get('FROM_EMAIL', 'noreply@yourapp.com')
        elif self.use_azure_communication:
            self.azure_comm_connection_string = os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING')
            self.azure_comm_sender_email = os.environ.get('AZURE_COMMUNICATION_SENDER_EMAIL')
            self.from_email = self.azure_comm_sender_email
        else:
            # Fallback to SMTP (for local development or non-Azure deployments)
            self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
            self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
            self.smtp_username = os.environ.get('SMTP_USERNAME')
            self.smtp_password = os.environ.get('SMTP_PASSWORD')
            self.from_email = os.environ.get('FROM_EMAIL', self.smtp_username)
        
        self.app_name = os.environ.get('APP_NAME', 'Rhythmic Project Manager')
        
        # Azure App Service detection
        self.is_azure = self._is_azure_environment()
    
    def generate_sharing_link(self, project_id: int, role: str = 'viewer', 
                            expires_hours: int = 24, max_uses: int = 1,
                            created_by: int = None) -> Tuple[str, str]:
        """
        Generate a secure sharing link for a project.
        
        Args:
            project_id: ID of the project to share
            role: Role to assign to users who use this link ('viewer', 'editor', 'admin')
            expires_hours: Number of hours until the link expires
            max_uses: Maximum number of times the link can be used
            created_by: ID of the user creating the link
            
        Returns:
            Tuple[str, str]: (sharing_url, token) - The complete sharing URL and the token
            
        Raises:
            SharingServiceError: If project doesn't exist or user lacks permission
        """
        from app import db, Project, SharingToken, SharingActivityLog
        
        # Validate project exists
        project = Project.query.get(project_id)
        if not project:
            raise SharingServiceError(f"Project with ID {project_id} not found")
        
        # Validate role
        valid_roles = ['viewer', 'editor', 'admin']
        if role not in valid_roles:
            raise SharingServiceError(f"Invalid role '{role}'. Must be one of: {valid_roles}")
        
        # Generate secure token
        token = SharingToken.generate_secure_token()
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        # Create sharing token record with error handling
        try:
            sharing_token = SharingToken(
                token=token,
                project_id=project_id,
                created_by=created_by,
                role=role,
                expires_at=expires_at,
                max_uses=max_uses,
                current_uses=0,
                is_active=True
            )
        except Exception as e:
            print(f"Error creating SharingToken: {str(e)}")
            raise SharingServiceError("Failed to create sharing token")
        
        try:
            db.session.add(sharing_token)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Database error creating sharing token: {str(e)}")
            raise SharingServiceError("Failed to save sharing token to database")
        
        # Log the activity
        try:
            SharingActivityLog.log_activity(
                project_id=project_id,
                action='token_generated',
                user_id=created_by,
                details=f"Sharing link generated for role '{role}', expires in {expires_hours} hours",
                ip_address=self._get_client_ip(),
                user_agent=self._get_user_agent()
            )
        except Exception as log_error:
            logger.warning(f"Failed to log activity for project {project_id}: {str(log_error)}")
            # Continue without logging if activity logging fails
        
        try:
            db.session.commit()
            logger.info(f"Sharing token generated for project {project_id}, role: {role}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to commit sharing token for project {project_id}: {str(e)}")
            raise SharingServiceError(f"Failed to create sharing token: {str(e)}")
        
        # Generate the complete sharing URL
        with current_app.app_context():
            sharing_url = url_for('accept_sharing_invitation', token=token, _external=True)
        
        return sharing_url, token
    
    def send_email_invitation(self, project_id: int, email: str, role: str = 'viewer',
                            message: str = "", expires_hours: int = 24,
                            created_by: int = None) -> Dict[str, Any]:
        """
        Send an email invitation to share a project.
        
        Args:
            project_id: ID of the project to share
            email: Email address to send invitation to
            role: Role to assign ('viewer', 'editor', 'admin')
            message: Optional personal message from the inviter
            expires_hours: Number of hours until the invitation expires
            created_by: ID of the user sending the invitation
            
        Returns:
            Dict[str, Any]: Result containing success status and details
            
        Raises:
            EmailDeliveryError: If email delivery fails
            SharingServiceError: If project doesn't exist or other validation fails
        """
        from app import db, User, Project, SharingToken, SharingActivityLog, InvitationNotification
        
        # Validate project exists
        project = Project.query.get(project_id)
        if not project:
            raise SharingServiceError(f"Project with ID {project_id} not found")
        
        # Get inviter information
        inviter = User.query.get(created_by) if created_by else None
        inviter_name = inviter.name if inviter else "Someone"
        
        # Generate sharing link
        sharing_url, token = self.generate_sharing_link(
            project_id=project_id,
            role=role,
            expires_hours=expires_hours,
            created_by=created_by
        )
        
        # Get the sharing token object
        sharing_token = SharingToken.query.filter_by(token=token).first()
        
        # Prepare email content
        subject = f"{inviter_name} invited you to collaborate on '{project.name}'"
        html_content = self._generate_email_template(
            project=project,
            inviter_name=inviter_name,
            role=role,
            sharing_url=sharing_url,
            personal_message=message,
            expires_hours=expires_hours
        )
        
        # Send email
        try:
            self._send_email(
                to_email=email,
                subject=subject,
                html_content=html_content
            )
            
            # Log successful email send
            SharingActivityLog.log_activity(
                project_id=project_id,
                action='project_shared',
                user_id=created_by,
                details=f"Email invitation sent to {email} for role '{role}'",
                ip_address=self._get_client_ip(),
                user_agent=self._get_user_agent()
            )
            
            # Create invitation notification
            InvitationNotification.create_notification(
                project_id=project_id,
                sender_user_id=created_by,
                notification_type='invitation_sent',
                recipient_email=email,
                sharing_token_id=sharing_token.id,
                message=f"Invitation sent to {email} for role '{role}'"
            )
            
            try:
                db.session.commit()
                logger.info(f"Email invitation sent successfully to {email} for project {project_id}")
            except Exception as db_error:
                db.session.rollback()
                logger.error(f"Database error after sending email to {email}: {str(db_error)}")
                raise SharingServiceError(f"Email sent but database update failed: {str(db_error)}")
            
            return {
                'success': True,
                'message': f'Invitation sent successfully to {email}',
                'sharing_url': sharing_url,
                'token': token,
                'expires_at': (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat()
            }
            
        except Exception as e:
            # Log failed email send
            SharingActivityLog.log_activity(
                project_id=project_id,
                action='email_failed',
                user_id=created_by,
                details=f"Failed to send email invitation to {email}: {str(e)}",
                ip_address=self._get_client_ip(),
                user_agent=self._get_user_agent()
            )
            
            db.session.commit()
            raise EmailDeliveryError(f"Failed to send email invitation: {str(e)}")

    def _generate_email_template(self, project, inviter_name: str, role: str,
                               sharing_url: str, personal_message: str = "",
                               expires_hours: int = 24) -> str:
        """
        Generate HTML email template for sharing invitations.
        
        Args:
            project: Project being shared
            inviter_name: Name of the person sending the invitation
            role: Role being assigned
            sharing_url: URL to accept the invitation
            personal_message: Optional personal message
            expires_hours: Hours until expiration
            
        Returns:
            str: HTML email content
        """
        role_descriptions = {
            'viewer': 'view the project and its tasks',
            'editor': 'view, create, and edit tasks',
            'admin': 'manage the project, tasks, and collaborators'
        }
        
        role_description = role_descriptions.get(role, 'collaborate on the project')
        expires_text = f"in {expires_hours} hours" if expires_hours < 48 else f"in {expires_hours // 24} days"
        
        with current_app.app_context():
            return render_template('emails/sharing_invitation.html',
                                 app_name=self.app_name,
                                 project=project,
                                 inviter_name=inviter_name,
                                 role=role,
                                 role_description=role_description,
                                 sharing_url=sharing_url,
                                 personal_message=personal_message,
                                 expires_text=expires_text)

    def _send_email(self, to_email: str, subject: str, html_content: str) -> None:
        """
        Send an email using SendGrid, Azure Communication Services, or SMTP fallback.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            
        Raises:
            EmailDeliveryError: If email delivery fails
        """
        if self.use_sendgrid:
            self._send_email_sendgrid(to_email, subject, html_content)
        elif self.use_azure_communication:
            self._send_email_azure(to_email, subject, html_content)
        else:
            self._send_email_smtp(to_email, subject, html_content)
    
    def _send_email_sendgrid(self, to_email: str, subject: str, html_content: str) -> None:
        """
        Send email using SendGrid API.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            
        Raises:
            EmailDeliveryError: If email delivery fails
        """
        try:
            # Try to import SendGrid
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            if not self.sendgrid_api_key:
                raise EmailDeliveryError("SendGrid API key not configured")
            
            # Create email message
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            # Send email
            sg = SendGridAPIClient(api_key=self.sendgrid_api_key)
            response = sg.send(message)
            
            if response.status_code not in [200, 201, 202]:
                raise EmailDeliveryError(f"SendGrid returned status code: {response.status_code}")
                
        except ImportError:
            raise EmailDeliveryError("SendGrid library not installed. Run: pip install sendgrid")
        except Exception as e:
            raise EmailDeliveryError(f"Failed to send email via SendGrid: {str(e)}")

    def _send_email_azure(self, to_email: str, subject: str, html_content: str) -> None:
        """
        Send email using Azure Communication Services.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            
        Raises:
            EmailDeliveryError: If email delivery fails
        """
        try:
            # Try to import Azure Communication Services
            from azure.communication.email import EmailClient
            from azure.communication.email.models import EmailMessage, EmailContent, EmailAddress, EmailRecipients
            
            if not self.azure_comm_connection_string or not self.azure_comm_sender_email:
                raise EmailDeliveryError("Azure Communication Services not properly configured")
            
            # Create email client
            email_client = EmailClient.from_connection_string(self.azure_comm_connection_string)
            
            # Create email message
            email_message = EmailMessage(
                sender=EmailAddress(email=self.azure_comm_sender_email, display_name=self.app_name),
                content=EmailContent(
                    subject=subject,
                    html=html_content
                ),
                recipients=EmailRecipients(
                    to=[EmailAddress(email=to_email)]
                )
            )
            
            # Send email
            response = email_client.send(email_message)
            
            if not response or not hasattr(response, 'message_id'):
                raise EmailDeliveryError("Failed to send email via Azure Communication Services")
                
        except ImportError:
            # Azure Communication Services not available, fall back to SMTP
            self._send_email_smtp(to_email, subject, html_content)
        except Exception as e:
            raise EmailDeliveryError(f"Failed to send email via Azure Communication Services: {str(e)}")
    
    def _send_email_smtp(self, to_email: str, subject: str, html_content: str) -> None:
        """
        Send email using SMTP (fallback method).
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            
        Raises:
            EmailDeliveryError: If email delivery fails
        """
        if not self.smtp_username or not self.smtp_password:
            raise EmailDeliveryError("SMTP credentials not configured")
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                
        except Exception as e:
            raise EmailDeliveryError(f"Failed to send email via SMTP: {str(e)}")

    def _get_client_ip(self) -> Optional[str]:
        """Get client IP address from request context."""
        if request:
            return request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        return None

    def _get_user_agent(self) -> Optional[str]:
        """Get user agent from request context."""
        if request:
            return request.headers.get('User-Agent')
        return None

    def process_sharing_token(self, token: str, user_id: int) -> Dict[str, Any]:
        """
        Process a sharing token to add a user to a project.
        
        Args:
            token: The sharing token to process
            user_id: ID of the user accepting the invitation
            
        Returns:
            Dict[str, Any]: Result containing success status and details
            
        Raises:
            InvalidTokenError: If token is invalid, expired, or exhausted
            SharingServiceError: If user is already a collaborator or other errors
        """
        from app import db, User, Project, ProjectCollaborator, SharingToken, SharingActivityLog, InvitationNotification
        
        # Find the sharing token
        sharing_token = SharingToken.query.filter_by(token=token, is_active=True).first()
        
        if not sharing_token:
            raise InvalidTokenError("Invalid or inactive sharing token")
        
        # Check if token has expired
        if sharing_token.expires_at and sharing_token.expires_at < datetime.utcnow():
            raise InvalidTokenError("Sharing token has expired")
        
        # Check if token has reached max uses
        if sharing_token.max_uses and sharing_token.current_uses >= sharing_token.max_uses:
            raise InvalidTokenError("Sharing token has been exhausted")
        
        # Get the project and user
        project = Project.query.get(sharing_token.project_id)
        user = User.query.get(user_id)
        
        if not project:
            raise SharingServiceError("Project not found")
        
        if not user:
            raise SharingServiceError("User not found")
        
        # Check if user is already a collaborator
        existing_collaborator = ProjectCollaborator.query.filter_by(
            project_id=project.id,
            user_id=user_id
        ).first()
        
        if existing_collaborator:
            return {
                'success': True,
                'message': f'You are already a collaborator on project "{project.name}"',
                'project_id': project.id,
                'role': existing_collaborator.role
            }
        
        # Check if user is the project owner
        if project.owner_id == user_id:
            return {
                'success': True,
                'message': f'You are the owner of project "{project.name}"',
                'project_id': project.id,
                'role': 'owner'
            }
        
        try:
            # Add user as collaborator
            collaborator = ProjectCollaborator(
                project_id=project.id,
                user_id=user_id,
                role=sharing_token.role,
                invited_by=sharing_token.created_by,
                invited_at=datetime.utcnow(),
                accepted_at=datetime.utcnow(),
                status=ProjectCollaborator.STATUS_ACCEPTED
            )
            
            db.session.add(collaborator)
            
            # Update token usage
            sharing_token.current_uses += 1
            
            # If token has reached max uses, deactivate it
            if sharing_token.max_uses and sharing_token.current_uses >= sharing_token.max_uses:
                sharing_token.is_active = False
            
            # Log the activity
            SharingActivityLog.log_activity(
                project_id=project.id,
                action='invitation_accepted',
                user_id=user_id,
                details=f"User {user.name} ({user.email}) accepted invitation for role '{sharing_token.role}'",
                ip_address=self._get_client_ip(),
                user_agent=self._get_user_agent()
            )
            
            # Create invitation notification
            InvitationNotification.create_notification(
                project_id=project.id,
                sender_user_id=sharing_token.created_by,
                notification_type='invitation_accepted',
                recipient_email=user.email,
                sharing_token_id=sharing_token.id,
                message=f"{user.name} accepted the invitation to join '{project.name}' as {sharing_token.role}"
            )
            
            db.session.commit()
            
            logger.info(f"User {user_id} successfully added to project {project.id} with role {sharing_token.role}")
            
            return {
                'success': True,
                'message': f'Successfully joined project "{project.name}" as {sharing_token.role}',
                'project_id': project.id,
                'role': sharing_token.role
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to process sharing token for user {user_id}: {str(e)}")
            raise SharingServiceError(f"Failed to process invitation: {str(e)}")

    def _is_azure_environment(self) -> bool:
        """
        Detect if the application is running in Azure App Service.
        
        Returns:
            bool: True if running in Azure, False otherwise
        """
        azure_indicators = [
            'WEBSITE_SITE_NAME',  # Azure App Service
            'WEBSITE_RESOURCE_GROUP',  # Azure App Service
            'APPSETTING_WEBSITE_SITE_NAME',  # Alternative Azure indicator
        ]
        
        return any(os.environ.get(indicator) for indicator in azure_indicators)