"""
Azure Communication Services Integration

Provides email and SMS capabilities using Azure Communication Services
with fallback to SMTP for email.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AzureCommunicationService:
    """Azure Communication Services integration"""
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING')
        self.sender_email = os.environ.get('AZURE_COMMUNICATION_SENDER_EMAIL')
        self.enabled = bool(self.connection_string and self.sender_email)
        self.email_client = None
        
        # Email templates for different notification types
        self.templates = {
            'invitation_sent': 'Project Invitation',
            'invitation_accepted': 'Invitation Accepted',
            'invitation_declined': 'Invitation Declined',
            'role_changed': 'Role Updated',
            'project_shared': 'Project Shared',
            'access_revoked': 'Access Revoked'
        }
        
        if self.enabled:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure Communication Services client"""
        try:
            from azure.communication.email import EmailClient
            
            self.email_client = EmailClient.from_connection_string(self.connection_string)
            logger.info("Azure Communication Services client initialized successfully")
            
        except ImportError:
            logger.warning("Azure Communication Services SDK not available")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize Azure Communication Services: {e}")
            self.enabled = False
    
    def is_available(self) -> bool:
        """Check if Azure Communication Services is available"""
        return self.enabled and self.email_client is not None
    
    def send_email(self, to_email: str, subject: str, html_content: str, 
                   plain_content: str = None) -> Dict[str, Any]:
        """Send email using Azure Communication Services"""
        if not self.is_available():
            return {
                'success': False,
                'error': 'Azure Communication Services not available',
                'fallback_required': True
            }
        
        try:
            from azure.communication.email.models import (
                EmailMessage, EmailContent, EmailAddress, EmailRecipients
            )
            
            # Create email message
            email_message = EmailMessage(
                sender=EmailAddress(
                    email=self.sender_email,
                    display_name="Rhythmic Project Manager"
                ),
                content=EmailContent(
                    subject=subject,
                    html=html_content,
                    plain_text=plain_content or self._html_to_plain(html_content)
                ),
                recipients=EmailRecipients(
                    to=[EmailAddress(email=to_email)]
                )
            )
            
            # Send email
            response = self.email_client.send(email_message)
            
            if response and hasattr(response, 'message_id'):
                logger.info(f"Email sent successfully via Azure Communication Services: {response.message_id}")
                return {
                    'success': True,
                    'message_id': response.message_id,
                    'service': 'azure_communication'
                }
            else:
                logger.error("Failed to send email - no message ID returned")
                return {
                    'success': False,
                    'error': 'No message ID returned',
                    'fallback_required': True
                }
                
        except Exception as e:
            logger.error(f"Failed to send email via Azure Communication Services: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_required': True
            }
    
    def send_invitation_email(self, to_email: str, project_name: str, 
                            inviter_name: str, role: str, invitation_url: str,
                            personal_message: str = "") -> Dict[str, Any]:
        """Send project invitation email"""
        subject = f"{inviter_name} invited you to collaborate on '{project_name}'"
        
        html_content = self._generate_invitation_html(
            project_name=project_name,
            inviter_name=inviter_name,
            role=role,
            invitation_url=invitation_url,
            personal_message=personal_message
        )
        
        return self.send_email(to_email, subject, html_content)
    
    def send_notification_email(self, to_email: str, notification_type: str,
                              project_name: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification email for various project events"""
        template_name = self.templates.get(notification_type, 'Project Notification')
        subject = f"{template_name} - {project_name}"
        
        html_content = self._generate_notification_html(
            notification_type=notification_type,
            project_name=project_name,
            details=details
        )
        
        return self.send_email(to_email, subject, html_content)
    
    def _generate_invitation_html(self, project_name: str, inviter_name: str,
                                role: str, invitation_url: str, personal_message: str = "") -> str:
        """Generate HTML content for invitation email"""
        role_descriptions = {
            'viewer': 'view the project and its tasks',
            'editor': 'view, create, and edit tasks',
            'admin': 'manage the project, tasks, and collaborators'
        }
        
        role_description = role_descriptions.get(role, 'collaborate on the project')
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Project Invitation</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #3B82F6; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #3B82F6; 
                          color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Project Invitation</h1>
                </div>
                <div class="content">
                    <h2>You've been invited to collaborate!</h2>
                    <p><strong>{inviter_name}</strong> has invited you to collaborate on the project <strong>"{project_name}"</strong>.</p>
                    <p>You'll be able to <strong>{role_description}</strong> as a <strong>{role}</strong>.</p>
                    {f'<div style="background-color: #e3f2fd; padding: 15px; border-left: 4px solid #2196f3; margin: 20px 0;"><p><em>"{personal_message}"</em></p></div>' if personal_message else ''}
                    <p>Click the button below to accept the invitation:</p>
                    <a href="{invitation_url}" class="button">Accept Invitation</a>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background-color: #f0f0f0; padding: 10px;">{invitation_url}</p>
                </div>
                <div class="footer">
                    <p>This invitation was sent by Rhythmic Project Manager</p>
                    <p>If you didn't expect this invitation, you can safely ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def _generate_notification_html(self, notification_type: str, project_name: str,
                                  details: Dict[str, Any]) -> str:
        """Generate HTML content for notification emails"""
        template_name = self.templates.get(notification_type, 'Project Notification')
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{template_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #3B82F6; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{template_name}</h1>
                </div>
                <div class="content">
                    <h2>Project: {project_name}</h2>
                    <p>{self._get_notification_message(notification_type, details)}</p>
                    <p>Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                </div>
                <div class="footer">
                    <p>This notification was sent by Rhythmic Project Manager</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def _get_notification_message(self, notification_type: str, details: Dict[str, Any]) -> str:
        """Get notification message based on type"""
        messages = {
            'invitation_accepted': f"Your invitation has been accepted by {details.get('user_name', 'a user')}.",
            'invitation_declined': f"Your invitation has been declined by {details.get('user_name', 'a user')}.",
            'role_changed': f"Your role has been changed to {details.get('new_role', 'unknown')}.",
            'access_revoked': "Your access to this project has been revoked.",
            'project_shared': f"Project has been shared with {details.get('recipient', 'collaborators')}."
        }
        
        return messages.get(notification_type, f"Project notification: {notification_type}")
    
    def _html_to_plain(self, html_content: str) -> str:
        """Convert HTML content to plain text (basic implementation)"""
        try:
            import re
            # Remove HTML tags
            plain = re.sub('<[^<]+?>', '', html_content)
            # Clean up whitespace
            plain = re.sub(r'\s+', ' ', plain).strip()
            return plain
        except:
            return "Please view this email in HTML format."
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status information"""
        return {
            'enabled': self.enabled,
            'connection_configured': bool(self.connection_string),
            'sender_email_configured': bool(self.sender_email),
            'client_initialized': self.email_client is not None,
            'service_name': 'Azure Communication Services'
        }


def create_communication_service(connection_string: str = None) -> AzureCommunicationService:
    """Create and configure Azure Communication Service"""
    return AzureCommunicationService(connection_string)