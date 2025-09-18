from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import pandas as pd
import io
import csv
import secrets
import re
from authlib.integrations.flask_client import OAuth
from services.ai_service import AIAssistant

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Important for OAuth flows

# Force HTTPS in production (Azure App Service)
if os.environ.get('FLASK_ENV') == 'production':
    app.config['PREFERRED_URL_SCHEME'] = 'https'

# Handle Azure App Service proxy headers
@app.before_request
def force_https():
    """Force HTTPS for OAuth redirects on Azure App Service"""
    if os.environ.get('FLASK_ENV') == 'production' or 'azurewebsites.net' in request.host:
        if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
            # Don't redirect, just ensure URL generation uses HTTPS
            pass

# Configure Azure services integration
try:
    from services.azure_services_config import configure_flask_app_with_azure_services
    from services.azure_security_config import configure_app_for_azure
    
    # Configure Azure services
    app = configure_flask_app_with_azure_services(app)
    
    # Configure Azure security settings
    app = configure_app_for_azure(app)
    
    print("Azure services integration configured successfully")
    
except ImportError as e:
    print(f"Azure services not available: {e}")
except Exception as e:
    print(f"Error configuring Azure services: {e}")

# Database configuration with fallback
try:
    from services.database_config import get_database_url, get_database_info
    database_url = get_database_url()
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print(f"Using database configuration from database_config.py")
        
except Exception as e:
    # Fallback to simple configuration if database_config fails
    print(f"Database config failed, using fallback: {e}")
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///instance/rhythmic.db')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # Handle SQLite relative paths
    if database_url.startswith('sqlite:///') and not database_url.startswith('sqlite:////'):
        db_path = database_url.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
            database_url = f'sqlite:///{db_path}'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)

# Initialize SocketIO with Azure-compatible configuration
try:
    from azure_websocket_config import get_azure_socketio_kwargs, configure_azure_headers
    
    # Configure Azure-specific headers
    app = configure_azure_headers(app)
    
    # Try to get Azure SignalR configuration
    signalr_config = app.config.get('AZURE_SIGNALR_CONFIG')
    if signalr_config and signalr_config.enabled:
        from services.azure_signalr_service import create_signalr_service
        azure_signalr = create_signalr_service()
        socketio_config = azure_signalr.get_flask_socketio_config()
        socketio = SocketIO(app, **socketio_config)
        print("SocketIO configured with Azure SignalR Service")
    else:
        # Use Azure-optimized WebSocket configuration
        azure_kwargs = get_azure_socketio_kwargs()
        socketio = SocketIO(app, **azure_kwargs)
        print("SocketIO configured with Azure-optimized WebSocket fallback")
        
except Exception as e:
    print(f"Error configuring SocketIO: {e}")
    # Fallback configuration
    socketio = SocketIO(app, 
                       cors_allowed_origins="*",
                       async_mode='threading',
                       transports=['polling', 'websocket'],
                       ping_timeout=60,
                       ping_interval=25,
                       logger=True, 
                       engineio_logger=False)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255))
    provider = db.Column(db.String(50), default='local')  # 'local', 'google', 'microsoft'
    provider_id = db.Column(db.String(120))  # OAuth provider user ID
    avatar_url = db.Column(db.String(200))  # Profile picture URL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', backref='owner', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # AI-generated project brief fields
    vision = db.Column(db.Text)
    problems = db.Column(db.Text)
    timeline = db.Column(db.Text)
    impact = db.Column(db.Text)
    goals = db.Column(db.Text)
    
    # Relationships
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')
    
    def get_collaborators(self):
        """Get all project collaborators with their roles"""
        return ProjectCollaborator.query.filter_by(
            project_id=self.id, 
            status=ProjectCollaborator.STATUS_ACCEPTED
        ).all()
    
    def has_collaborator(self, user_id):
        """Check if user is a collaborator"""
        if self.owner_id == user_id:
            return True
        
        collaborator = ProjectCollaborator.query.filter_by(
            project_id=self.id,
            user_id=user_id,
            status=ProjectCollaborator.STATUS_ACCEPTED
        ).first()
        return collaborator is not None
    
    def get_user_role(self, user_id):
        """Get user's role in this project"""
        if self.owner_id == user_id:
            return 'owner'
        
        collaborator = ProjectCollaborator.query.filter_by(
            project_id=self.id,
            user_id=user_id,
            status=ProjectCollaborator.STATUS_ACCEPTED
        ).first()
        
        return collaborator.role if collaborator else None
    
    def is_accessible_by(self, user_id):
        """Check if project is accessible by user"""
        return self.has_collaborator(user_id)
    
    def get_collaborator_count(self):
        """Get the total number of accepted collaborators (including owner)"""
        return ProjectCollaborator.query.filter_by(
            project_id=self.id,
            status=ProjectCollaborator.STATUS_ACCEPTED
        ).count() + 1  # +1 for owner
    
    def transfer_ownership(self, new_owner_id, current_user_id):
        """Transfer project ownership to another user"""
        # Verify current user is the owner
        if self.owner_id != current_user_id:
            raise ValueError("Only the current owner can transfer ownership")
        
        # Check if new owner is already a collaborator
        existing_collaborator = ProjectCollaborator.query.filter_by(
            project_id=self.id,
            user_id=new_owner_id,
            status=ProjectCollaborator.STATUS_ACCEPTED
        ).first()
        
        # If new owner was a collaborator, remove their collaborator record
        if existing_collaborator:
            db.session.delete(existing_collaborator)
        
        # Create a collaborator record for the old owner with admin role
        old_owner_collaborator = ProjectCollaborator(
            project_id=self.id,
            user_id=current_user_id,
            role='admin',
            invited_by=new_owner_id,
            status=ProjectCollaborator.STATUS_ACCEPTED,
            accepted_at=datetime.utcnow()
        )
        
        # Update project ownership
        self.owner_id = new_owner_id
        self.updated_at = datetime.utcnow()
        
        # Add the old owner as admin collaborator
        db.session.add(old_owner_collaborator)
        
        return True

class Label(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(7), default='#3B82F6')  # Hex color code
    icon = db.Column(db.String(50), default='fas fa-tag')  # FontAwesome icon class
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', backref='labels')
    tasks = db.relationship('Task', secondary='task_labels', back_populates='labels')

class TaskLabel(db.Model):
    __tablename__ = 'task_labels'
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), primary_key=True)
    label_id = db.Column(db.Integer, db.ForeignKey('label.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TaskDependency(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    depends_on_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    dependency_type = db.Column(db.String(20), default='finish_to_start')  # finish_to_start, start_to_start, finish_to_finish, start_to_finish
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    task = db.relationship('Task', foreign_keys=[task_id], back_populates='dependencies')
    depends_on = db.relationship('Task', foreign_keys=[depends_on_id], back_populates='dependents')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='backlog')
    priority = db.Column(db.String(20), default='medium')
    size = db.Column(db.String(20), default='medium')
    parent_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    
    # Advanced Task Management Fields
    sort_order = db.Column(db.Integer, default=0)  # For drag-and-drop reordering
    risk_level = db.Column(db.String(20), default='low')  # low, medium, high, critical
    risk_description = db.Column(db.Text)  # Description of potential risks
    mitigation_plan = db.Column(db.Text)  # Plan to mitigate identified risks
    is_expanded = db.Column(db.Boolean, default=True)  # For hierarchy view
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = db.relationship('User', backref='tasks')
    children = db.relationship('Task', backref=db.backref('parent', remote_side=[id]), lazy=True)
    labels = db.relationship('Label', secondary='task_labels', back_populates='tasks')
    
    # Dependency relationships
    dependencies = db.relationship('TaskDependency', foreign_keys='TaskDependency.task_id', back_populates='task')
    dependents = db.relationship('TaskDependency', foreign_keys='TaskDependency.depends_on_id', back_populates='depends_on')

# Sharing Models
class ProjectCollaborator(db.Model):
    __tablename__ = 'project_collaborators'
    
    # Role definitions with permissions
    ROLES = {
        'owner': {'level': 4, 'permissions': ['all']},
        'admin': {'level': 3, 'permissions': ['edit_project', 'manage_collaborators', 'edit_tasks']},
        'editor': {'level': 2, 'permissions': ['edit_tasks', 'create_tasks']},
        'viewer': {'level': 1, 'permissions': ['view_only']}
    }
    
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_DECLINED = 'declined'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='viewer')
    invited_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invited_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default=STATUS_PENDING)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('collaborators', cascade='all, delete-orphan'))
    user = db.relationship('User', foreign_keys=[user_id], backref='collaborations')
    inviter = db.relationship('User', foreign_keys=[invited_by])
    
    # Unique constraint to prevent duplicate collaborators
    __table_args__ = (db.UniqueConstraint('project_id', 'user_id', name='unique_project_collaborator'),)
    
    def has_permission(self, permission):
        """Check if the collaborator has a specific permission"""
        if self.role not in self.ROLES:
            return False
        
        role_permissions = self.ROLES[self.role]['permissions']
        return 'all' in role_permissions or permission in role_permissions
    
    def get_role_level(self):
        """Get the numeric level of the role for comparison"""
        return self.ROLES.get(self.role, {}).get('level', 0)
    
    def can_manage_role(self, target_role):
        """Check if this collaborator can manage another role"""
        if self.role == 'owner':
            return True
        if self.role == 'admin':
            return target_role in ['viewer', 'editor']
        return False

class SharingToken(db.Model):
    __tablename__ = 'sharing_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), unique=True, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='viewer')
    expires_at = db.Column(db.DateTime, nullable=False)
    max_uses = db.Column(db.Integer, default=1)
    current_uses = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('sharing_tokens', cascade='all, delete-orphan'))
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def is_valid(self):
        """Check if the token is valid for use"""
        return (self.is_active and 
                self.expires_at > datetime.utcnow() and 
                self.current_uses < self.max_uses)
    
    @staticmethod
    def generate_secure_token():
        """Generate a cryptographically secure token"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def consume_use(self):
        """Increment the usage count"""
        self.current_uses += 1
        if self.current_uses >= self.max_uses:
            self.is_active = False

class SharingActivityLog(db.Model):
    __tablename__ = 'sharing_activity_log'
    
    ACTION_TYPES = [
        'project_shared', 'collaborator_added', 'collaborator_removed',
        'role_changed', 'access_granted', 'access_revoked',
        'token_generated', 'token_used', 'suspicious_access'
    ]
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('activity_logs', cascade='all, delete-orphan'))
    user = db.relationship('User', backref='sharing_activities')
    
    @staticmethod
    def log_activity(project_id, action, user_id=None, details=None, ip_address=None, user_agent=None):
        """Helper method to log sharing activities"""
        activity = SharingActivityLog(
            project_id=project_id,
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(activity)
        return activity

class ActiveSession(db.Model):
    __tablename__ = 'active_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    session_id = db.Column(db.String(255), unique=True, nullable=False)
    connected_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='active_sessions')
    project = db.relationship('Project', backref=db.backref('active_sessions', cascade='all, delete-orphan'))
    
    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    @staticmethod
    def cleanup_inactive_sessions(timeout_minutes=30):
        """Remove sessions that have been inactive for too long"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        inactive_sessions = ActiveSession.query.filter(ActiveSession.last_activity < cutoff_time).all()
        for session in inactive_sessions:
            db.session.delete(session)
        return len(inactive_sessions)

class InvitationNotification(db.Model):
    __tablename__ = 'invitation_notifications'
    
    NOTIFICATION_TYPES = [
        'invitation_sent',
        'invitation_accepted', 
        'invitation_declined',
        'invitation_expired',
        'invitation_revoked'
    ]
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    sharing_token_id = db.Column(db.Integer, db.ForeignKey('sharing_tokens.id'))
    recipient_email = db.Column(db.String(120))
    recipient_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sender_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('invitation_notifications', cascade='all, delete-orphan'))
    sharing_token = db.relationship('SharingToken', backref='notifications')
    recipient_user = db.relationship('User', foreign_keys=[recipient_user_id], backref='received_notifications')
    sender_user = db.relationship('User', foreign_keys=[sender_user_id], backref='sent_notifications')
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
    
    @staticmethod
    def create_notification(project_id, sender_user_id, notification_type, 
                          recipient_email=None, recipient_user_id=None, 
                          sharing_token_id=None, message=None):
        """Create a new invitation notification"""
        notification = InvitationNotification(
            project_id=project_id,
            sender_user_id=sender_user_id,
            notification_type=notification_type,
            recipient_email=recipient_email,
            recipient_user_id=recipient_user_id,
            sharing_token_id=sharing_token_id,
            message=message
        )
        db.session.add(notification)
        return notification

# Initialize database tables
try:
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")
except Exception as e:
    print(f"Error creating database tables: {e}")
    # Don't raise - let the app continue

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    access_token_url='https://oauth2.googleapis.com/token',
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

github = oauth.register(
    name='github',
    client_id=os.environ.get('GITHUB_CLIENT_ID'),
    client_secret=os.environ.get('GITHUB_CLIENT_SECRET'),
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# WebSocket Handler for Real-time Collaboration
class ProjectWebSocketHandler:
    def __init__(self):
        self.active_connections = {}  # {user_id: {project_id: session_id}}
        self.project_rooms = {}       # {project_id: set(user_ids)}
    
    def connect(self, user_id, project_id, session_id):
        """Handle new WebSocket connection with authentication"""
        try:
            # Verify user has access to the project
            project = Project.query.get(project_id)
            if not project or not project.is_accessible_by(user_id):
                return False
            
            # Initialize user connections if not exists
            if user_id not in self.active_connections:
                self.active_connections[user_id] = {}
            
            # Store connection
            self.active_connections[user_id][project_id] = session_id
            
            # Add user to project room
            if project_id not in self.project_rooms:
                self.project_rooms[project_id] = set()
            self.project_rooms[project_id].add(user_id)
            
            # Create or update active session in database
            existing_session = ActiveSession.query.filter_by(
                user_id=user_id, 
                project_id=project_id
            ).first()
            
            if existing_session:
                existing_session.session_id = session_id
                existing_session.last_activity = datetime.utcnow()
            else:
                new_session = ActiveSession(
                    user_id=user_id,
                    project_id=project_id,
                    session_id=session_id
                )
                db.session.add(new_session)
            
            db.session.commit()
            
            # Notify other users in the project about new connection
            user = User.query.get(user_id)
            self.broadcast_update(project_id, 'user_connected', {
                'user_id': user_id,
                'user_name': user.name,
                'timestamp': datetime.utcnow().isoformat()
            }, exclude_user=user_id)
            
            return True
            
        except Exception as e:
            print(f"Error in WebSocket connect: {e}")
            return False
    
    def disconnect(self, user_id, project_id):
        """Handle WebSocket disconnection"""
        try:
            # Remove from active connections
            if user_id in self.active_connections:
                if project_id in self.active_connections[user_id]:
                    del self.active_connections[user_id][project_id]
                
                # Clean up empty user entry
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove from project room
            if project_id in self.project_rooms:
                self.project_rooms[project_id].discard(user_id)
                
                # Clean up empty project room
                if not self.project_rooms[project_id]:
                    del self.project_rooms[project_id]
            
            # Remove active session from database
            ActiveSession.query.filter_by(
                user_id=user_id, 
                project_id=project_id
            ).delete()
            db.session.commit()
            
            # Notify other users about disconnection
            user = User.query.get(user_id)
            if user:
                self.broadcast_update(project_id, 'user_disconnected', {
                    'user_id': user_id,
                    'user_name': user.name,
                    'timestamp': datetime.utcnow().isoformat()
                }, exclude_user=user_id)
            
        except Exception as e:
            print(f"Error in WebSocket disconnect: {e}")
    
    def broadcast_update(self, project_id, update_type, data, exclude_user=None):
        """Broadcast update to all project collaborators"""
        try:
            if project_id not in self.project_rooms:
                return
            
            message = {
                'type': update_type,
                'data': data,
                'timestamp': datetime.utcnow().isoformat(),
                'project_id': project_id
            }
            
            # Send to all users in the project room
            for user_id in self.project_rooms[project_id]:
                if exclude_user and user_id == exclude_user:
                    continue
                
                if (user_id in self.active_connections and 
                    project_id in self.active_connections[user_id]):
                    
                    session_id = self.active_connections[user_id][project_id]
                    socketio.emit('project_update', message, room=session_id)
            
        except Exception as e:
            print(f"Error broadcasting update: {e}")
    
    def send_to_user(self, user_id, project_id, message):
        """Send message to specific user"""
        try:
            if (user_id in self.active_connections and 
                project_id in self.active_connections[user_id]):
                
                session_id = self.active_connections[user_id][project_id]
                socketio.emit('direct_message', message, room=session_id)
                
        except Exception as e:
            print(f"Error sending message to user: {e}")
    
    def get_active_users(self, project_id):
        """Get list of active users for a project"""
        if project_id not in self.project_rooms:
            return []
        
        active_users = []
        for user_id in self.project_rooms[project_id]:
            user = User.query.get(user_id)
            if user:
                active_users.append({
                    'id': user_id,
                    'name': user.name,
                    'avatar_url': user.avatar_url
                })
        
        return active_users

# Initialize WebSocket handler
ws_handler = ProjectWebSocketHandler()

# Initialize Azure services
azure_signalr_service = None
azure_communication_service = None
azure_service_bus_service = None

try:
    from services.azure_signalr_service import create_signalr_service
    from services.azure_communication_service import create_communication_service
    from services.azure_service_bus_service import AzureServiceBusService
    
    # Initialize Azure SignalR Service
    azure_signalr_service = create_signalr_service()
    if azure_signalr_service.is_available():
        azure_signalr_service.set_fallback_handler(ws_handler)
        print("Azure SignalR Service initialized successfully")
    else:
        print("Azure SignalR Service not available, using local WebSocket fallback")
    
    # Initialize Azure Communication Services
    azure_communication_service = create_communication_service()
    if azure_communication_service.is_available():
        print("Azure Communication Services initialized successfully")
    else:
        print("Azure Communication Services not available, using SMTP fallback")
    
    # Initialize Azure Service Bus
    azure_service_bus_service = AzureServiceBusService()
    if azure_service_bus_service.is_available():
        print("Azure Service Bus initialized successfully")
    else:
        print("Azure Service Bus not available, using in-memory fallback")
    
    # Store services in app context for use in routes
    app.azure_signalr_service = azure_signalr_service
    app.azure_communication_service = azure_communication_service
    app.azure_service_bus_service = azure_service_bus_service
    
except ImportError as e:
    print(f"Azure services modules not available: {e}")
except Exception as e:
    print(f"Error initializing Azure services: {e}")

# SocketIO Event Handlers
@socketio.on('connect')
def handle_connect(auth):
    """Handle client connection"""
    if not current_user.is_authenticated:
        disconnect()
        return False
    
    print(f"User {current_user.id} ({current_user.name}) connected")
    return True

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    if current_user.is_authenticated:
        print(f"User {current_user.id} ({current_user.name}) disconnected")
        
        # Clean up all project connections for this user
        if current_user.id in ws_handler.active_connections:
            project_ids = list(ws_handler.active_connections[current_user.id].keys())
            for project_id in project_ids:
                ws_handler.disconnect(current_user.id, project_id)

@socketio.on('join_project')
def handle_join_project(data):
    """Handle user joining a project room"""
    if not current_user.is_authenticated:
        return
    
    project_id = data.get('project_id')
    if not project_id:
        emit('error', {'message': 'Project ID is required'})
        return
    
    # Verify access and connect
    if ws_handler.connect(current_user.id, project_id, request.sid):
        join_room(f"project_{project_id}")
        
        # Send current active users to the newly connected user
        active_users = ws_handler.get_active_users(project_id)
        emit('active_users', {'users': active_users})
        
        # Send confirmation
        emit('joined_project', {
            'project_id': project_id,
            'message': 'Successfully joined project'
        })
        
        print(f"User {current_user.id} joined project {project_id}")
    else:
        emit('error', {'message': 'Access denied or project not found'})

@socketio.on('leave_project')
def handle_leave_project(data):
    """Handle user leaving a project room"""
    if not current_user.is_authenticated:
        return
    
    project_id = data.get('project_id')
    if not project_id:
        return
    
    leave_room(f"project_{project_id}")
    ws_handler.disconnect(current_user.id, project_id)
    
    emit('left_project', {
        'project_id': project_id,
        'message': 'Successfully left project'
    })
    
    print(f"User {current_user.id} left project {project_id}")

@socketio.on('task_update')
def handle_task_update(data):
    """Handle real-time task updates"""
    if not current_user.is_authenticated:
        return
    
    project_id = data.get('project_id')
    task_data = data.get('task_data')
    update_type = data.get('update_type', 'task_update')
    
    if not project_id or not task_data:
        emit('error', {'message': 'Project ID and task data are required'})
        return
    
    # Verify user has permission to update tasks
    project = Project.query.get(project_id)
    if not project or not project.is_accessible_by(current_user.id):
        emit('error', {'message': 'Access denied'})
        return
    
    # Broadcast the update to all project collaborators
    update_data = {
        'task_data': task_data,
        'user': {
            'id': current_user.id,
            'name': current_user.name
        },
        'update_type': update_type
    }
    
    ws_handler.broadcast_update(project_id, 'task_update', update_data, exclude_user=current_user.id)

@socketio.on('project_update')
def handle_project_update(data):
    """Handle real-time project updates"""
    if not current_user.is_authenticated:
        return
    
    project_id = data.get('project_id')
    project_data = data.get('project_data')
    update_type = data.get('update_type', 'project_update')
    
    if not project_id or not project_data:
        emit('error', {'message': 'Project ID and project data are required'})
        return
    
    # Verify user has permission to update project
    project = Project.query.get(project_id)
    if not project or not project.is_accessible_by(current_user.id):
        emit('error', {'message': 'Access denied'})
        return
    
    # Broadcast the update to all project collaborators
    update_data = {
        'project_data': project_data,
        'user': {
            'id': current_user.id,
            'name': current_user.name
        },
        'update_type': update_type
    }
    
    ws_handler.broadcast_update(project_id, 'project_update', update_data, exclude_user=current_user.id)

@socketio.on('get_active_users')
def handle_get_active_users(data):
    """Get active users for a project"""
    if not current_user.is_authenticated:
        return
    
    project_id = data.get('project_id')
    if not project_id:
        emit('error', {'message': 'Project ID is required'})
        return
    
    # Verify access
    project = Project.query.get(project_id)
    if not project or not project.is_accessible_by(current_user.id):
        emit('error', {'message': 'Access denied'})
        return
    
    active_users = ws_handler.get_active_users(project_id)
    emit('active_users', {'users': active_users})

@socketio.on('sync_state')
def handle_sync_state(data):
    """Synchronize state after reconnection"""
    if not current_user.is_authenticated:
        return
    
    project_id = data.get('project_id')
    last_sync = data.get('last_sync')
    
    if not project_id:
        emit('error', {'message': 'Project ID is required'})
        return
    
    # Verify access
    project = Project.query.get(project_id)
    if not project or not project.is_accessible_by(current_user.id):
        emit('error', {'message': 'Access denied'})
        return
    
    try:
        # Get recent activity since last sync
        if last_sync:
            sync_time = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
            recent_activities = SharingActivityLog.query.filter(
                SharingActivityLog.project_id == project_id,
                SharingActivityLog.created_at > sync_time,
                SharingActivityLog.action.in_(['task_created', 'task_updated', 'task_deleted', 'project_updated'])
            ).order_by(SharingActivityLog.created_at.desc()).limit(50).all()
            
            # Send recent updates
            for activity in reversed(recent_activities):  # Send in chronological order
                if activity.action in ['task_created', 'task_updated', 'task_deleted']:
                    # Get current task data if it still exists
                    if activity.action != 'task_deleted':
                        task = Task.query.filter_by(project_id=project_id).filter(
                            Task.title.contains(activity.details.split("'")[1]) if "'" in activity.details else False
                        ).first()
                        
                        if task:
                            task_data = {
                                'id': task.id,
                                'title': task.title,
                                'description': task.description,
                                'status': task.status,
                                'priority': task.priority,
                                'size': task.size,
                                'owner_id': task.owner_id,
                                'owner_name': task.owner.name,
                                'start_date': task.start_date.isoformat() if task.start_date else None,
                                'end_date': task.end_date.isoformat() if task.end_date else None,
                                'parent_id': task.parent_id,
                                'risk_level': task.risk_level,
                                'created_at': task.created_at.isoformat(),
                                'updated_at': task.updated_at.isoformat()
                            }
                            
                            emit('project_update', {
                                'type': 'task_update',
                                'data': {
                                    'task_data': task_data,
                                    'user': {
                                        'id': activity.user_id,
                                        'name': activity.user.name if activity.user else 'Unknown'
                                    },
                                    'update_type': activity.action.replace('_', '_').replace('created', 'create').replace('updated', 'update').replace('deleted', 'delete')
                                },
                                'timestamp': activity.created_at.isoformat(),
                                'project_id': project_id,
                                'is_sync': True
                            })
        
        # Send current active users
        active_users = ws_handler.get_active_users(project_id)
        emit('active_users', {'users': active_users})
        
        # Confirm sync completion
        emit('sync_complete', {
            'project_id': project_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"Error in sync_state: {e}")
        emit('error', {'message': 'Failed to synchronize state'})

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('projects'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            
            # Check for pending sharing token
            if 'pending_sharing_token' in session:
                token = session.pop('pending_sharing_token')
                try:
                    from services.sharing_service import SharingService
                    sharing_service = SharingService()
                    result = sharing_service.process_sharing_token(token, user.id)
                    flash(result['message'], 'success')
                    return redirect(url_for('projects'))
                except Exception as e:
                    flash(f'Error processing invitation: {str(e)}', 'error')
                    return redirect(url_for('projects'))
            
            # Check for next parameter (from invitation redirect)
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/sharing/accept/'):
                return redirect(next_page)
            
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return render_template('register.html')
        
        user = User(
            email=email,
            name=name,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        
        # Check for pending sharing token
        if 'pending_sharing_token' in session:
            token = session.get('pending_sharing_token')
            flash('Account created successfully! Now accepting your project invitation.', 'success')
            return redirect(url_for('accept_sharing_invitation', token=token))
        
        # Check for next parameter (from invitation redirect)
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/sharing/accept/'):
            flash('Account created successfully! Now accepting your project invitation.', 'success')
            return redirect(next_page)
        
        flash('Account created successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Helper function to generate secure redirect URIs
def get_redirect_uri(endpoint):
    """Generate redirect URI with HTTPS for production"""
    # Check if we're on Azure App Service
    if 'azurewebsites.net' in request.host:
        # Manually construct HTTPS URL for Azure
        return f"https://{request.host}{url_for(endpoint)}"
    else:
        # Use normal URL generation for local development
        return url_for(endpoint, _external=True)

# OAuth Routes
@app.route('/login/google')
def login_google():
    redirect_uri = get_redirect_uri('authorize_google')
    
    # Check if there's a pending sharing token and include it in the state
    state = None
    if 'pending_sharing_token' in session:
        state = session['pending_sharing_token']
    
    return google.authorize_redirect(redirect_uri, state=state)

@app.route('/login/github')
def login_github():
    redirect_uri = get_redirect_uri('authorize_github')
    return github.authorize_redirect(redirect_uri)

@app.route('/authorize/google')
def authorize_google():
    try:
        token = google.authorize_access_token()
        
        # Get the state parameter (which contains the sharing token if present)
        sharing_token = request.args.get('state')
        
        # Get user info from Google API
        resp = google.get('https://www.googleapis.com/oauth2/v2/userinfo', token=token)
        user_info = resp.json()
        
        if user_info and user_info.get('email'):
            email = user_info.get('email')
            name = user_info.get('name', email.split('@')[0])
            provider_id = user_info.get('id')
            avatar_url = user_info.get('picture')
            
            # Check if user exists
            user = User.query.filter_by(email=email, provider='google').first()
            
            if not user:
                # Check if email exists with different provider
                existing_user = User.query.filter_by(email=email).first()
                if existing_user:
                    flash('An account with this email already exists. Please use the original login method.')
                    return redirect(url_for('login'))
                
                # Create new user
                user = User(
                    email=email,
                    name=name,
                    provider='google',
                    provider_id=provider_id,
                    avatar_url=avatar_url
                )
                db.session.add(user)
                db.session.commit()
            
            login_user(user)
            
            # Check for pending sharing token
            if 'pending_sharing_token' in session:
                token = session.pop('pending_sharing_token')
                try:
                    from services.sharing_service import SharingService
                    sharing_service = SharingService()
                    result = sharing_service.process_sharing_token(token, user.id)
                    flash(result['message'], 'success')
                    return redirect(url_for('projects'))
                except Exception as e:
                    flash(f'Error processing invitation: {str(e)}', 'error')
                    return redirect(url_for('projects'))
            
            return redirect(url_for('index'))
        else:
            flash('Failed to get user information from Google')
            return redirect(url_for('login'))
    except Exception as e:
        flash(f'Google authentication failed: {str(e)}')
        return redirect(url_for('login'))

@app.route('/authorize/github')
def authorize_github():
    try:
        token = github.authorize_access_token()
        resp = github.get('user', token=token)
        user_info = resp.json()
        
        email = user_info.get('email')
        if not email:
            # Get primary email if not public
            resp = github.get('user/emails', token=token)
            emails = resp.json()
            primary_email = next((e['email'] for e in emails if e['primary']), None)
            email = primary_email
        
        if email:
            name = user_info.get('name') or user_info.get('login')
            provider_id = str(user_info.get('id'))
            avatar_url = user_info.get('avatar_url')
            
            # Check if user exists
            user = User.query.filter_by(email=email, provider='github').first()
            
            if not user:
                # Check if email exists with different provider
                existing_user = User.query.filter_by(email=email).first()
                if existing_user:
                    flash('An account with this email already exists. Please use the original login method.')
                    return redirect(url_for('login'))
                
                # Create new user
                user = User(
                    email=email,
                    name=name,
                    provider='github',
                    provider_id=provider_id,
                    avatar_url=avatar_url
                )
                db.session.add(user)
                db.session.commit()
            
            login_user(user)
            
            # Check for pending sharing token
            if 'pending_sharing_token' in session:
                token = session.pop('pending_sharing_token')
                try:
                    from services.sharing_service import SharingService
                    sharing_service = SharingService()
                    result = sharing_service.process_sharing_token(token, user.id)
                    flash(result['message'], 'success')
                    return redirect(url_for('projects'))
                except Exception as e:
                    flash(f'Error processing invitation: {str(e)}', 'error')
                    return redirect(url_for('projects'))
            
            return redirect(url_for('index'))
        else:
            flash('Failed to get email from GitHub')
            return redirect(url_for('login'))
    except Exception as e:
        flash(f'GitHub authentication failed: {str(e)}')
        return redirect(url_for('login'))

@app.route('/projects')
@login_required
def projects():
    from services.permission_manager import PermissionManager
    
    # Get all accessible projects (owned + shared)
    accessible_project_ids = PermissionManager.get_accessible_projects(current_user.id)
    
    if accessible_project_ids:
        projects = Project.query.filter(Project.id.in_(accessible_project_ids)).all()
    else:
        projects = []
    
    # Add role information for each project
    projects_with_roles = []
    for project in projects:
        user_role = PermissionManager.get_user_role(current_user.id, project.id)
        project_data = {
            'project': project,
            'user_role': user_role,
            'is_owner': project.owner_id == current_user.id,
            'collaborator_count': project.get_collaborator_count()
        }
        projects_with_roles.append(project_data)
    
    return render_template('projects.html', projects=projects_with_roles)

@app.route('/test-css')
def test_css():
    """Simple test page to verify CSS is working"""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CSS Test - Rhythmic</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body class="bg-black text-white font-inter antialiased p-8">
    <div class="max-w-4xl mx-auto">
        <h1 class="text-4xl font-bold gradient-text mb-8">CSS Test Page</h1>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Test Tailwind CSS -->
            <div class="bg-gray-800 p-6 rounded-lg">
                <h2 class="text-xl font-semibold mb-4">Tailwind CSS Test</h2>
                <p class="text-gray-300 mb-4">If you can see this styled properly, Tailwind is working.</p>
                <button class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded">
                    Tailwind Button
                </button>
            </div>
            
            <!-- Test Custom CSS -->
            <div class="glass p-6 rounded-lg">
                <h2 class="text-xl font-semibold mb-4">Custom CSS Test</h2>
                <p class="text-gray-300 mb-4">If this box has a glass effect, custom CSS is working.</p>
                <button class="btn-primary px-4 py-2 rounded">
                    Custom Button
                </button>
            </div>
        </div>
        
        <div class="mt-8 p-4 bg-green-900/20 border border-green-500/30 rounded-lg">
            <h3 class="text-green-400 font-semibold mb-2">What to Check:</h3>
            <ul class="text-green-300 space-y-1">
                <li>• The title should have a blue-purple gradient</li>
                <li>• The right box should have a glass/blur effect</li>
                <li>• The custom button should have a gradient background</li>
                <li>• Text should be white on black background</li>
            </ul>
        </div>
        
        <div class="mt-4 text-center">
            <a href="/" class="text-blue-400 hover:text-blue-300">← Back to Home</a>
        </div>
    </div>
</body>
</html>
    '''

@app.route('/projects/new', methods=['GET', 'POST'])
@login_required
def new_project():
    if request.method == 'POST':
        project = Project(
            name=request.form['name'],
            description=request.form['description'],
            owner_id=current_user.id,
            vision=request.form.get('vision', ''),
            problems=request.form.get('problems', ''),
            timeline=request.form.get('timeline', ''),
            impact=request.form.get('impact', ''),
            goals=request.form.get('goals', '')
        )
        db.session.add(project)
        db.session.commit()
        return redirect(url_for('view_project', id=project.id))
    
    return render_template('new_project.html')

@app.route('/projects/<int:id>')
@login_required
def view_project(id):
    from services.permission_manager import PermissionManager
    
    project = Project.query.get_or_404(id)
    
    # Check if user has access to view this project
    if not PermissionManager.can_access_project(current_user.id, id):
        flash('Access denied to this project')
        return redirect(url_for('projects'))
    
    # Get user's role and permissions for this project
    user_role = PermissionManager.get_user_role(current_user.id, id)
    user_permissions = {
        'can_edit_project': PermissionManager.has_permission(current_user.id, id, 'edit_project'),
        'can_edit_tasks': PermissionManager.has_permission(current_user.id, id, 'edit_tasks'),
        'can_create_tasks': PermissionManager.has_permission(current_user.id, id, 'create_tasks'),
        'can_delete_project': PermissionManager.has_permission(current_user.id, id, 'delete_project'),
        'can_manage_collaborators': PermissionManager.has_permission(current_user.id, id, 'manage_collaborators'),
        'is_owner': project.owner_id == current_user.id
    }
    
    # Get tasks with hierarchy, ordered by sort_order
    tasks = Task.query.filter_by(project_id=id).order_by(Task.sort_order, Task.created_at).all()
    
    # Convert tasks to dictionaries for JSON serialization
    tasks_data = []
    for task in tasks:
        task_dict = {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'start_date': task.start_date.strftime('%Y-%m-%d') if task.start_date else None,
            'end_date': task.end_date.strftime('%Y-%m-%d') if task.end_date else None,
            'status': task.status,
            'priority': task.priority,
            'size': task.size,
            'parent_id': task.parent_id,
            'sort_order': task.sort_order,
            'risk_level': task.risk_level,
            'risk_description': task.risk_description,
            'mitigation_plan': task.mitigation_plan,
            'is_expanded': task.is_expanded,
            'owner_name': task.owner.name if task.owner else 'Unknown',
            'labels': [{'id': label.id, 'name': label.name, 'color': label.color, 'icon': label.icon} for label in task.labels],
            'dependencies': [{'id': dep.id, 'depends_on_id': dep.depends_on_id, 'depends_on_title': dep.depends_on.title, 'dependency_type': dep.dependency_type} for dep in task.dependencies],
            'dependents': [{'id': dep.id, 'task_id': dep.task_id, 'task_title': dep.task.title, 'dependency_type': dep.dependency_type} for dep in task.dependents]
        }
        tasks_data.append(task_dict)
    
    # Get labels for the project
    labels = Label.query.filter_by(project_id=id).all()
    
    # Get collaborators for display
    collaborators = project.get_collaborators()
    
    return render_template('project_detail.html', 
                         project=project, 
                         tasks=tasks, 
                         tasks_data=tasks_data, 
                         labels=labels,
                         user_role=user_role,
                         user_permissions=user_permissions,
                         collaborators=collaborators)

@app.route('/projects/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(id):
    from services.permission_manager import PermissionManager
    
    project = Project.query.get_or_404(id)
    
    # Check if user has permission to edit this project
    if not PermissionManager.has_permission(current_user.id, id, 'edit_project'):
        flash('You do not have permission to edit this project')
        return redirect(url_for('view_project', id=id))
    
    if request.method == 'POST':
        project.name = request.form['name']
        project.description = request.form['description']
        project.vision = request.form.get('vision', '')
        project.problems = request.form.get('problems', '')
        project.timeline = request.form.get('timeline', '')
        project.impact = request.form.get('impact', '')
        project.goals = request.form.get('goals', '')
        project.updated_at = datetime.utcnow()
        
        # Log the activity
        SharingActivityLog.log_activity(
            project_id=id,
            action='project_updated',
            user_id=current_user.id,
            details=f"Project '{project.name}' updated by {current_user.name}",
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        # Emit real-time update for project update
        project_data = {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'vision': project.vision,
            'problems': project.problems,
            'timeline': project.timeline,
            'impact': project.impact,
            'goals': project.goals,
            'updated_at': project.updated_at.isoformat()
        }
        
        ws_handler.broadcast_update(id, 'project_update', {
            'project_data': project_data,
            'user': {
                'id': current_user.id,
                'name': current_user.name
            },
            'update_type': 'project_update'
        })
        
        flash('Project updated successfully')
        return redirect(url_for('view_project', id=id))
    
    return render_template('edit_project.html', project=project)

@app.route('/projects/<int:id>/delete', methods=['POST'])
@login_required
def delete_project(id):
    from services.permission_manager import PermissionManager
    
    project = Project.query.get_or_404(id)
    
    # Check if user has permission to delete this project (only owners can delete)
    if not PermissionManager.has_permission(current_user.id, id, 'delete_project'):
        flash('Only the project owner can delete this project')
        return redirect(url_for('view_project', id=id))
    
    project_name = project.name
    
    # Log the activity before deletion
    SharingActivityLog.log_activity(
        project_id=id,
        action='project_deleted',
        user_id=current_user.id,
        details=f"Project '{project_name}' deleted by {current_user.name}",
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    db.session.delete(project)
    db.session.commit()
    flash(f'Project "{project_name}" has been deleted')
    return redirect(url_for('projects'))

# Task routes
@app.route('/projects/<int:project_id>/tasks/new', methods=['GET', 'POST'])
@login_required
def new_task(project_id):
    from services.permission_manager import PermissionManager
    
    project = Project.query.get_or_404(project_id)
    
    # Check if user has permission to create tasks
    if not PermissionManager.has_permission(current_user.id, project_id, 'create_tasks'):
        flash('You do not have permission to create tasks in this project')
        return redirect(url_for('view_project', id=project_id))
    
    if request.method == 'POST':
        # Get the next sort order for this project
        max_sort_order = db.session.query(db.func.max(Task.sort_order)).filter_by(project_id=project_id).scalar() or 0
        
        task = Task(
            title=request.form['title'],
            description=request.form['description'],
            project_id=project_id,
            owner_id=current_user.id,
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date() if request.form['start_date'] else None,
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form['end_date'] else None,
            status=request.form['status'],
            priority=request.form['priority'],
            size=request.form['size'],
            parent_id=int(request.form['parent_id']) if request.form['parent_id'] else None,
            sort_order=max_sort_order + 1,
            risk_level=request.form.get('risk_level', 'low'),
            risk_description=request.form.get('risk_description', ''),
            mitigation_plan=request.form.get('mitigation_plan', '')
        )
        db.session.add(task)
        db.session.flush()  # Get the task ID
        
        # Handle labels
        label_ids = request.form.getlist('labels')
        for label_id in label_ids:
            if label_id:  # Skip empty values
                task_label = TaskLabel(task_id=task.id, label_id=int(label_id))
                db.session.add(task_label)
        
        # Log the activity
        SharingActivityLog.log_activity(
            project_id=project_id,
            action='task_created',
            user_id=current_user.id,
            details=f"Task '{task.title}' created by {current_user.name}",
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        # Emit real-time update for task creation
        task_data = {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'size': task.size,
            'owner_id': task.owner_id,
            'owner_name': current_user.name,
            'start_date': task.start_date.isoformat() if task.start_date else None,
            'end_date': task.end_date.isoformat() if task.end_date else None,
            'parent_id': task.parent_id,
            'risk_level': task.risk_level,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat()
        }
        
        ws_handler.broadcast_update(project_id, 'task_update', {
            'task_data': task_data,
            'user': {
                'id': current_user.id,
                'name': current_user.name
            },
            'update_type': 'task_create'
        })
        
        flash('Task created successfully')
        return redirect(url_for('view_project', id=project_id))
    
    # Get existing tasks for parent selection and labels for selection
    tasks = Task.query.filter_by(project_id=project_id).all()
    labels = Label.query.filter_by(project_id=project_id).all()
    return render_template('new_task.html', project=project, tasks=tasks, labels=labels)

@app.route('/projects/<int:project_id>/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(project_id, task_id):
    from services.permission_manager import PermissionManager
    
    project = Project.query.get_or_404(project_id)
    task = Task.query.get_or_404(task_id)
    
    # Check if user has permission to edit tasks and task belongs to project
    if not PermissionManager.has_permission(current_user.id, project_id, 'edit_tasks') or task.project_id != project_id:
        flash('You do not have permission to edit tasks in this project')
        return redirect(url_for('view_project', id=project_id))
    
    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form['description']
        task.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date() if request.form['start_date'] else None
        task.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form['end_date'] else None
        task.status = request.form['status']
        task.priority = request.form['priority']
        task.size = request.form['size']
        task.parent_id = int(request.form['parent_id']) if request.form['parent_id'] else None
        task.risk_level = request.form.get('risk_level', 'low')
        task.risk_description = request.form.get('risk_description', '')
        task.mitigation_plan = request.form.get('mitigation_plan', '')
        task.updated_at = datetime.utcnow()
        
        # Handle labels - remove existing and add new ones
        TaskLabel.query.filter_by(task_id=task_id).delete()
        label_ids = request.form.getlist('labels')
        for label_id in label_ids:
            if label_id:  # Skip empty values
                task_label = TaskLabel(task_id=task_id, label_id=int(label_id))
                db.session.add(task_label)
        
        # Log the activity
        SharingActivityLog.log_activity(
            project_id=project_id,
            action='task_updated',
            user_id=current_user.id,
            details=f"Task '{task.title}' updated by {current_user.name}",
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        # Emit real-time update for task update
        task_data = {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'size': task.size,
            'owner_id': task.owner_id,
            'owner_name': task.owner.name,
            'start_date': task.start_date.isoformat() if task.start_date else None,
            'end_date': task.end_date.isoformat() if task.end_date else None,
            'parent_id': task.parent_id,
            'risk_level': task.risk_level,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat()
        }
        
        ws_handler.broadcast_update(project_id, 'task_update', {
            'task_data': task_data,
            'user': {
                'id': current_user.id,
                'name': current_user.name
            },
            'update_type': 'task_update'
        })
        
        flash('Task updated successfully')
        return redirect(url_for('view_project', id=project_id))
    
    tasks = Task.query.filter_by(project_id=project_id).filter(Task.id != task_id).all()
    labels = Label.query.filter_by(project_id=project_id).all()
    return render_template('edit_task.html', project=project, task=task, tasks=tasks, labels=labels)

@app.route('/projects/<int:project_id>/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(project_id, task_id):
    from services.permission_manager import PermissionManager
    
    project = Project.query.get_or_404(project_id)
    task = Task.query.get_or_404(task_id)
    
    # Check if user has permission to edit tasks (which includes deleting) and task belongs to project
    if not PermissionManager.has_permission(current_user.id, project_id, 'edit_tasks') or task.project_id != project_id:
        flash('You do not have permission to delete tasks in this project')
        return redirect(url_for('view_project', id=project_id))
    
    task_title = task.title
    
    # Log the activity before deletion
    SharingActivityLog.log_activity(
        project_id=project_id,
        action='task_deleted',
        user_id=current_user.id,
        details=f"Task '{task_title}' deleted by {current_user.name}",
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    # Emit real-time update for task deletion
    task_data = {
        'id': task.id,
        'title': task_title
    }
    
    ws_handler.broadcast_update(project_id, 'task_update', {
        'task_data': task_data,
        'user': {
            'id': current_user.id,
            'name': current_user.name
        },
        'update_type': 'task_delete'
    })
    
    db.session.delete(task)
    db.session.commit()
    flash(f'Task "{task_title}" has been deleted')
    return redirect(url_for('view_project', id=project_id))

# CSV Import/Export
@app.route('/projects/<int:id>/export')
@login_required
def export_project(id):
    project = Project.query.get_or_404(id)
    if project.owner_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('projects'))
    
    tasks = Task.query.filter_by(project_id=id).all()
    
    # Create CSV data
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Title', 'Description', 'Start Date', 'End Date', 'Status', 'Priority', 'Size', 'Parent ID'])
    
    for task in tasks:
        writer.writerow([
            task.title,
            task.description or '',
            task.start_date.strftime('%Y-%m-%d') if task.start_date else '',
            task.end_date.strftime('%Y-%m-%d') if task.end_date else '',
            task.status,
            task.priority,
            task.size,
            task.parent_id or ''
        ])
    
    output.seek(0)
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': f'attachment; filename={project.name}_tasks.csv'
    }

@app.route('/projects/<int:id>/import', methods=['GET', 'POST'])
@login_required
def import_project(id):
    project = Project.query.get_or_404(id)
    if project.owner_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('projects'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(url_for('import_project', id=id))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(url_for('import_project', id=id))
        
        if file and file.filename.endswith('.csv'):
            try:
                df = pd.read_csv(file)
                for _, row in df.iterrows():
                    task = Task(
                        title=row['Title'],
                        description=row.get('Description', ''),
                        project_id=id,
                        owner_id=current_user.id,
                        start_date=pd.to_datetime(row.get('Start Date')).date() if pd.notna(row.get('Start Date')) else None,
                        end_date=pd.to_datetime(row.get('End Date')).date() if pd.notna(row.get('End Date')) else None,
                        status=row.get('Status', 'backlog'),
                        priority=row.get('Priority', 'medium'),
                        size=row.get('Size', 'medium'),
                        parent_id=int(row['Parent ID']) if pd.notna(row.get('Parent ID')) else None
                    )
                    db.session.add(task)
                db.session.commit()
                flash('Tasks imported successfully')
            except Exception as e:
                flash(f'Error importing file: {str(e)}')
        else:
            flash('Please select a CSV file')
    
    return render_template('import_project.html', project=project)

# Label Management Routes
@app.route('/projects/<int:project_id>/labels')
@login_required
def project_labels(project_id):
    """Get all labels for a project"""
    from services.permission_manager import PermissionManager
    
    project = Project.query.get_or_404(project_id)
    
    # Check if user has access to view the project
    if not PermissionManager.can_access_project(current_user.id, project_id):
        return jsonify({'error': 'Access denied to this project'}), 403
    
    labels = Label.query.filter_by(project_id=project_id).all()
    labels_data = []
    for label in labels:
        labels_data.append({
            'id': label.id,
            'name': label.name,
            'color': label.color,
            'icon': label.icon,
            'task_count': len(label.tasks)
        })
    
    return jsonify({'labels': labels_data})

@app.route('/projects/<int:project_id>/labels', methods=['POST'])
@login_required
def create_label(project_id):
    """Create a new label for a project"""
    from services.permission_manager import PermissionManager
    
    project = Project.query.get_or_404(project_id)
    
    # Check if user has permission to edit the project (required for creating labels)
    if not PermissionManager.has_permission(current_user.id, project_id, 'edit_project'):
        return jsonify({'error': 'Insufficient permissions to create labels'}), 403
    
    data = request.get_json()
    name = data.get('name', '').strip()
    color = data.get('color', '#3B82F6')
    icon = data.get('icon', 'fas fa-tag')
    
    if not name:
        return jsonify({'error': 'Label name is required'}), 400
    
    # Check if label name already exists in this project
    existing_label = Label.query.filter_by(project_id=project_id, name=name).first()
    if existing_label:
        return jsonify({'error': 'Label with this name already exists'}), 400
    
    # Check label limit (50 per project as per PRD)
    label_count = Label.query.filter_by(project_id=project_id).count()
    if label_count >= 50:
        return jsonify({'error': 'Maximum of 50 labels per project allowed'}), 400
    
    label = Label(
        name=name,
        color=color,
        icon=icon,
        project_id=project_id
    )
    db.session.add(label)
    db.session.commit()
    
    return jsonify({
        'id': label.id,
        'name': label.name,
        'color': label.color,
        'icon': label.icon,
        'task_count': 0
    }), 201

@app.route('/projects/<int:project_id>/labels/<int:label_id>', methods=['PUT'])
@login_required
def update_label(project_id, label_id):
    """Update a label"""
    from services.permission_manager import PermissionManager
    
    project = Project.query.get_or_404(project_id)
    
    # Check if user has permission to edit the project (required for updating labels)
    if not PermissionManager.has_permission(current_user.id, project_id, 'edit_project'):
        return jsonify({'error': 'Insufficient permissions to update labels'}), 403
    
    label = Label.query.filter_by(id=label_id, project_id=project_id).first()
    if not label:
        return jsonify({'error': 'Label not found'}), 404
    
    data = request.get_json()
    name = data.get('name', '').strip()
    color = data.get('color', label.color)
    icon = data.get('icon', label.icon)
    
    if not name:
        return jsonify({'error': 'Label name is required'}), 400
    
    # Check if another label with this name exists
    existing_label = Label.query.filter_by(project_id=project_id, name=name).filter(Label.id != label_id).first()
    if existing_label:
        return jsonify({'error': 'Label with this name already exists'}), 400
    
    label.name = name
    label.color = color
    label.icon = icon
    db.session.commit()
    
    return jsonify({
        'id': label.id,
        'name': label.name,
        'color': label.color,
        'icon': label.icon,
        'task_count': len(label.tasks)
    })

@app.route('/projects/<int:project_id>/labels/<int:label_id>', methods=['DELETE'])
@login_required
def delete_label(project_id, label_id):
    """Delete a label"""
    from services.permission_manager import PermissionManager
    
    project = Project.query.get_or_404(project_id)
    
    # Check if user has permission to edit the project (required for deleting labels)
    if not PermissionManager.has_permission(current_user.id, project_id, 'edit_project'):
        return jsonify({'error': 'Insufficient permissions to delete labels'}), 403
    
    label = Label.query.filter_by(id=label_id, project_id=project_id).first()
    if not label:
        return jsonify({'error': 'Label not found'}), 404
    
    # Remove all task associations
    TaskLabel.query.filter_by(label_id=label_id).delete()
    db.session.delete(label)
    db.session.commit()
    
    return jsonify({'message': 'Label deleted successfully'})

@app.route('/projects/<int:project_id>/tasks/<int:task_id>/labels', methods=['POST'])
@login_required
def add_task_label(project_id, task_id):
    """Add a label to a task"""
    from services.permission_manager import PermissionManager
    
    project = Project.query.get_or_404(project_id)
    task = Task.query.get_or_404(task_id)
    
    # Check if user has permission to edit tasks and task belongs to project
    if not PermissionManager.has_permission(current_user.id, project_id, 'edit_tasks') or task.project_id != project_id:
        return jsonify({'error': 'Insufficient permissions to modify task labels'}), 403
    
    data = request.get_json()
    label_id = data.get('label_id')
    
    if not label_id:
        return jsonify({'error': 'Label ID is required'}), 400
    
    label = Label.query.filter_by(id=label_id, project_id=project_id).first()
    if not label:
        return jsonify({'error': 'Label not found'}), 404
    
    # Check if association already exists
    existing_association = TaskLabel.query.filter_by(task_id=task_id, label_id=label_id).first()
    if existing_association:
        return jsonify({'error': 'Label already assigned to this task'}), 400
    
    task_label = TaskLabel(task_id=task_id, label_id=label_id)
    db.session.add(task_label)
    db.session.commit()
    
    return jsonify({'message': 'Label added to task successfully'})

@app.route('/projects/<int:project_id>/tasks/<int:task_id>/labels/<int:label_id>', methods=['DELETE'])
@login_required
def remove_task_label(project_id, task_id, label_id):
    """Remove a label from a task"""
    from services.permission_manager import PermissionManager
    
    project = Project.query.get_or_404(project_id)
    task = Task.query.get_or_404(task_id)
    
    # Check if user has permission to edit tasks and task belongs to project
    if not PermissionManager.has_permission(current_user.id, project_id, 'edit_tasks') or task.project_id != project_id:
        return jsonify({'error': 'Insufficient permissions to modify task labels'}), 403
    
    task_label = TaskLabel.query.filter_by(task_id=task_id, label_id=label_id).first()
    if not task_label:
        return jsonify({'error': 'Label not found on this task'}), 404
    
    db.session.delete(task_label)
    db.session.commit()
    
    return jsonify({'message': 'Label removed from task successfully'})

# AI Assistant Routes
@app.route('/api/generate-brief', methods=['POST'])
@login_required
def generate_project_brief():
    """Generate AI-powered project brief"""
    try:
        data = request.get_json()
        project_name = data.get('project_name', '')
        user_input = data.get('user_input', '')
        
        if not project_name or not user_input:
            return jsonify({'error': 'Project name and user input are required'}), 400
        
        ai_assistant = AIAssistant()
        brief = ai_assistant.generate_project_brief(project_name, user_input)
        
        return jsonify({'brief': brief})
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate brief: {str(e)}'}), 500

@app.route('/api/generate-starter-plan', methods=['POST'])
@login_required
def generate_starter_plan():
    """Generate AI-powered starter project plan"""
    try:
        data = request.get_json()
        project_name = data.get('project_name', '')
        project_brief = data.get('project_brief', {})
        
        if not project_name:
            return jsonify({'error': 'Project name is required'}), 400
        
        ai_assistant = AIAssistant()
        tasks = ai_assistant.generate_starter_project_plan(project_name, project_brief)
        
        return jsonify({'tasks': tasks})
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate starter plan: {str(e)}'}), 500

@app.route('/api/generate-summary', methods=['POST'])
@login_required
def generate_project_summary():
    """Generate AI-powered project summary"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        
        if not project_id:
            return jsonify({'error': 'Project ID is required'}), 400
        
        project = Project.query.get_or_404(project_id)
        if project.owner_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get project brief
        project_brief = {
            'vision': project.vision or '',
            'problems': project.problems or '',
            'timeline': project.timeline or '',
            'impact': project.impact or '',
            'goals': project.goals or ''
        }
        
        # Get tasks
        tasks = Task.query.filter_by(project_id=project_id).all()
        tasks_data = []
        for task in tasks:
            tasks_data.append({
                'title': task.title,
                'status': task.status
            })
        
        ai_assistant = AIAssistant()
        summary = ai_assistant.generate_project_summary(project.name, tasks_data, project_brief)
        
        return jsonify({'summary': summary})
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate summary: {str(e)}'}), 500

@app.route('/projects/<int:project_id>/generate-tasks', methods=['POST'])
@login_required
def generate_starter_tasks(project_id):
    """Generate AI-powered starter tasks for a project"""
    from services.permission_manager import PermissionManager
    
    try:
        project = Project.query.get_or_404(project_id)
        
        # Check if user has permission to create tasks
        if not PermissionManager.has_permission(current_user.id, project_id, 'create_tasks'):
            return jsonify({'error': 'Insufficient permissions to create tasks'}), 403
        
        # Get project brief
        project_brief = {
            'vision': project.vision or '',
            'problems': project.problems or '',
            'timeline': project.timeline or '',
            'impact': project.impact or '',
            'goals': project.goals or ''
        }
        
        ai_assistant = AIAssistant()
        tasks = ai_assistant.generate_starter_project_plan(project.name, project_brief)
        
        # Create tasks in database
        created_tasks = []
        for task_data in tasks:
            # Calculate start and end dates based on suggested offset and duration
            start_offset = task_data.get('suggested_start_offset', 0)
            duration = task_data.get('estimated_duration', 5)
            
            start_date = datetime.now().date() + timedelta(days=start_offset)
            end_date = start_date + timedelta(days=duration)
            
            task = Task(
                title=task_data.get('title', 'Untitled Task'),
                description=task_data.get('description', ''),
                project_id=project_id,
                owner_id=current_user.id,
                start_date=start_date,
                end_date=end_date,
                status='backlog',
                priority=task_data.get('priority', 'medium'),
                size=task_data.get('size', 'medium')
            )
            db.session.add(task)
            created_tasks.append(task)
        
        db.session.commit()
        
        return jsonify({
            'message': f'Successfully created {len(created_tasks)} starter tasks',
            'tasks_created': len(created_tasks)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to generate starter tasks: {str(e)}'}), 500

# Advanced Task Management API Routes
@app.route('/api/projects/<int:project_id>/tasks/reorder', methods=['POST'])
@login_required
def reorder_tasks(project_id):
    """Reorder tasks via drag-and-drop"""
    from services.permission_manager import PermissionManager
    
    try:
        project = Project.query.get_or_404(project_id)
        
        # Check if user has permission to edit tasks
        if not PermissionManager.has_permission(current_user.id, project_id, 'edit_tasks'):
            return jsonify({'error': 'Insufficient permissions to reorder tasks'}), 403
        
        data = request.get_json()
        task_orders = data.get('task_orders', [])  # List of {task_id: int, sort_order: int}
        
        for item in task_orders:
            task = Task.query.filter_by(id=item['task_id'], project_id=project_id).first()
            if task:
                task.sort_order = item['sort_order']
        
        db.session.commit()
        return jsonify({'message': 'Tasks reordered successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to reorder tasks: {str(e)}'}), 500

@app.route('/api/projects/<int:project_id>/tasks/<int:task_id>/toggle-expand', methods=['POST'])
@login_required
def toggle_task_expand(project_id, task_id):
    """Toggle task expansion state for hierarchy view"""
    from services.permission_manager import PermissionManager
    
    try:
        project = Project.query.get_or_404(project_id)
        task = Task.query.get_or_404(task_id)
        
        # Check if user has access to view the project and task belongs to project
        if not PermissionManager.can_access_project(current_user.id, project_id) or task.project_id != project_id:
            return jsonify({'error': 'Access denied to this project'}), 403
        
        task.is_expanded = not task.is_expanded
        db.session.commit()
        
        return jsonify({'is_expanded': task.is_expanded})
        
    except Exception as e:
        return jsonify({'error': f'Failed to toggle task expansion: {str(e)}'}), 500

@app.route('/api/projects/<int:project_id>/tasks/<int:task_id>/dependencies', methods=['POST'])
@login_required
def add_task_dependency(project_id, task_id):
    """Add a dependency to a task"""
    from services.permission_manager import PermissionManager
    
    try:
        project = Project.query.get_or_404(project_id)
        task = Task.query.get_or_404(task_id)
        
        # Check if user has permission to edit tasks and task belongs to project
        if not PermissionManager.has_permission(current_user.id, project_id, 'edit_tasks') or task.project_id != project_id:
            return jsonify({'error': 'Insufficient permissions to modify task dependencies'}), 403
        
        data = request.get_json()
        depends_on_id = data.get('depends_on_id')
        dependency_type = data.get('dependency_type', 'finish_to_start')
        
        if not depends_on_id:
            return jsonify({'error': 'depends_on_id is required'}), 400
        
        # Check if dependency task exists in the same project
        depends_on_task = Task.query.filter_by(id=depends_on_id, project_id=project_id).first()
        if not depends_on_task:
            return jsonify({'error': 'Dependency task not found'}), 404
        
        # Prevent self-dependency
        if task_id == depends_on_id:
            return jsonify({'error': 'Task cannot depend on itself'}), 400
        
        # Check for circular dependencies
        if would_create_circular_dependency(task_id, depends_on_id):
            return jsonify({'error': 'This would create a circular dependency'}), 400
        
        # Check if dependency already exists
        existing = TaskDependency.query.filter_by(task_id=task_id, depends_on_id=depends_on_id).first()
        if existing:
            return jsonify({'error': 'Dependency already exists'}), 400
        
        dependency = TaskDependency(
            task_id=task_id,
            depends_on_id=depends_on_id,
            dependency_type=dependency_type
        )
        db.session.add(dependency)
        db.session.commit()
        
        return jsonify({
            'id': dependency.id,
            'task_id': task_id,
            'depends_on_id': depends_on_id,
            'depends_on_title': depends_on_task.title,
            'dependency_type': dependency_type
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to add dependency: {str(e)}'}), 500

@app.route('/api/projects/<int:project_id>/tasks/<int:task_id>/dependencies/<int:dependency_id>', methods=['DELETE'])
@login_required
def remove_task_dependency(project_id, task_id, dependency_id):
    """Remove a dependency from a task"""
    from services.permission_manager import PermissionManager
    
    try:
        project = Project.query.get_or_404(project_id)
        task = Task.query.get_or_404(task_id)
        
        # Check if user has permission to edit tasks and task belongs to project
        if not PermissionManager.has_permission(current_user.id, project_id, 'edit_tasks') or task.project_id != project_id:
            return jsonify({'error': 'Insufficient permissions to modify task dependencies'}), 403
        
        dependency = TaskDependency.query.filter_by(id=dependency_id, task_id=task_id).first()
        if not dependency:
            return jsonify({'error': 'Dependency not found'}), 404
        
        db.session.delete(dependency)
        db.session.commit()
        
        return jsonify({'message': 'Dependency removed successfully'})
        
    except Exception as e:
        return jsonify({'error': f'Failed to remove dependency: {str(e)}'}), 500

def would_create_circular_dependency(task_id, depends_on_id):
    """Check if adding a dependency would create a circular dependency"""
    # Simple check: if the task we're depending on already depends on us (directly or indirectly)
    visited = set()
    to_check = [depends_on_id]
    
    while to_check:
        current_id = to_check.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)
        
        if current_id == task_id:
            return True
        
        # Get all tasks that the current task depends on
        dependencies = TaskDependency.query.filter_by(task_id=current_id).all()
        for dep in dependencies:
            if dep.depends_on_id not in visited:
                to_check.append(dep.depends_on_id)
    
    return False

# Sharing invitation acceptance routes
@app.route('/sharing/accept/<token>')
def accept_sharing_invitation(token):
    """Display sharing invitation acceptance page with token validation."""
    from services.sharing_service import SharingService, InvalidTokenError, SharingServiceError
    
    # Validate token and get invitation details
    sharing_token = SharingToken.query.filter_by(token=token).first()
    
    if not sharing_token:
        return render_template('sharing_invitation.html',
                             invitation_valid=False,
                             error_message="This invitation link is invalid or has been removed.",
                             token=token)
    
    if not sharing_token.is_valid():
        error_message = "This invitation has expired." if sharing_token.expires_at < datetime.utcnow() else "This invitation has been used up."
        return render_template('sharing_invitation.html',
                             invitation_valid=False,
                             error_message=error_message,
                             token=token)
    
    # Get project and inviter details
    project = Project.query.get(sharing_token.project_id)
    inviter = User.query.get(sharing_token.created_by)
    
    if not project or not inviter:
        return render_template('sharing_invitation.html',
                             invitation_valid=False,
                             error_message="The project or inviter associated with this invitation no longer exists.",
                             token=token)
    
    # Check if current user is already a collaborator
    if current_user.is_authenticated:
        existing_collaborator = ProjectCollaborator.query.filter_by(
            project_id=project.id,
            user_id=current_user.id
        ).first()
        
        if existing_collaborator and existing_collaborator.status == ProjectCollaborator.STATUS_ACCEPTED:
            flash(f'You are already a collaborator on "{project.name}".', 'info')
            return redirect(url_for('view_project', id=project.id))
    
    # Role descriptions for display
    role_descriptions = {
        'viewer': 'view the project and its tasks',
        'editor': 'view, create, and edit tasks',
        'admin': 'manage the project, tasks, and collaborators'
    }
    
    # Role colors for styling
    role_colors = {
        'owner': 'red',
        'admin': 'orange',
        'editor': 'blue',
        'viewer': 'gray'
    }
    
    return render_template('sharing_invitation.html',
                         invitation_valid=True,
                         token=token,
                         project_name=project.name,
                         project_description=project.description,
                         inviter_name=inviter.name,
                         role=sharing_token.role,
                         role_description=role_descriptions.get(sharing_token.role, 'collaborate on the project'),
                         role_color=role_colors.get(sharing_token.role, 'blue'),
                         expiry_date=sharing_token.expires_at,
                         max_uses=sharing_token.max_uses,
                         remaining_uses=sharing_token.max_uses - sharing_token.current_uses)

@app.route('/sharing/accept/<token>', methods=['POST'])
def process_sharing_invitation(token):
    """Process sharing invitation acceptance."""
    from services.sharing_service import SharingService, InvalidTokenError, SharingServiceError
    
    if not current_user.is_authenticated:
        # Store token in session and redirect to login
        session['pending_sharing_token'] = token
        flash('Please log in to accept the project invitation.', 'info')
        return redirect(url_for('login'))
    
    try:
        sharing_service = SharingService()
        result = sharing_service.process_sharing_token(token, current_user.id)
        
        flash(result['message'], 'success')
        
        # Log successful invitation acceptance
        SharingActivityLog.log_activity(
            project_id=result['project']['id'],
            action='invitation_accepted',
            user_id=current_user.id,
            details=f"User '{current_user.name}' accepted invitation and joined as '{result['project']['role']}'",
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return redirect(url_for('view_project', id=result['project']['id']))
        
    except InvalidTokenError as e:
        flash(f'Invalid or expired invitation: {str(e)}', 'error')
        return redirect(url_for('projects'))
        
    except SharingServiceError as e:
        flash(f'Error accepting invitation: {str(e)}', 'error')
        return redirect(url_for('projects'))
        
    except Exception as e:
        flash(f'Unexpected error: {str(e)}', 'error')
        return redirect(url_for('projects'))

@app.route('/sharing/decline/<token>', methods=['POST'])
def decline_sharing_invitation(token):
    """Decline a sharing invitation."""
    from services.sharing_service import SharingService, InvalidTokenError, SharingServiceError
    
    if not current_user.is_authenticated:
        flash('Please log in to decline the project invitation.', 'info')
        return redirect(url_for('login'))
    
    try:
        sharing_service = SharingService()
        result = sharing_service.decline_invitation(token, current_user.id)
        
        flash(result['message'], 'info')
        return redirect(url_for('projects'))
        
    except InvalidTokenError as e:
        flash(f'Invalid or expired invitation: {str(e)}', 'error')
        return redirect(url_for('projects'))
        
    except SharingServiceError as e:
        flash(f'Error declining invitation: {str(e)}', 'error')
        return redirect(url_for('projects'))
        
    except Exception as e:
        flash(f'Unexpected error: {str(e)}', 'error')
        return redirect(url_for('projects'))

# Sharing Management API Endpoints
@app.route('/api/projects/<int:id>/share', methods=['POST'])
@login_required
def share_project(id):
    """Create a sharing invitation for a project."""
    try:
        from services.sharing_service import SharingService, SharingServiceError, EmailDeliveryError
        from services.permission_manager import PermissionManager
        
        # Check if user has permission to share the project
        if not PermissionManager.has_permission(current_user.id, id, 'manage_collaborators'):
            return jsonify({
                'error': 'Insufficient permissions to share this project'
            }), 403
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        method = data.get('method', 'link')
        role = data.get('role', 'viewer')
        expires_hours = data.get('expires_hours', 24)
        message = data.get('message', '')
        
        # Validate role
        valid_roles = ['viewer', 'editor', 'admin']
        if role not in valid_roles:
            return jsonify({
                'error': f'Invalid role. Must be one of: {valid_roles}'
            }), 400
        
        # Validate expires_hours
        if not isinstance(expires_hours, int) or expires_hours < 1 or expires_hours > 8760:  # Max 1 year
            return jsonify({
                'error': 'expires_hours must be an integer between 1 and 8760'
            }), 400
        
        sharing_service = SharingService()
        
        if method == 'email':
            email = data.get('email')
            if not email:
                return jsonify({'error': 'Email address is required for email sharing'}), 400
            
            # Basic email validation
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                return jsonify({'error': 'Invalid email address format'}), 400
            
            result = sharing_service.send_email_invitation(
                project_id=id,
                email=email,
                role=role,
                message=message,
                expires_hours=expires_hours,
                created_by=current_user.id
            )
            
            return jsonify({
                'success': True,
                'method': 'email',
                'message': result['message'],
                'sharing_url': result['sharing_url'],
                'expires_at': result['expires_at']
            })
        
        elif method in ['link', 'text']:
            sharing_url, token = sharing_service.generate_sharing_link(
                project_id=id,
                role=role,
                expires_hours=expires_hours,
                created_by=current_user.id
            )
            
            return jsonify({
                'success': True,
                'method': method,
                'sharing_url': sharing_url,
                'token': token,
                'expires_at': (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat(),
                'message': f'Sharing link generated successfully'
            })
        
        else:
            return jsonify({
                'error': 'Invalid sharing method. Must be one of: email, link, text'
            }), 400
    
    except EmailDeliveryError as e:
        return jsonify({
            'error': f'Failed to send email invitation: {str(e)}'
        }), 500
    
    except SharingServiceError as e:
        return jsonify({
            'error': str(e)
        }), 400
    
    except Exception as e:
        return jsonify({
            'error': f'Unexpected error: {str(e)}'
        }), 500


@app.route('/api/projects/<int:id>/collaborators', methods=['GET'])
@login_required
def get_project_collaborators(id):
    """Get all collaborators for a project."""
    try:
        from services.permission_manager import PermissionManager
        
        # Check if user has access to the project
        if not PermissionManager.can_access_project(current_user.id, id):
            return jsonify({
                'error': 'Access denied to this project'
            }), 403
        
        project = Project.query.get_or_404(id)
        
        # Get all accepted collaborators
        collaborators = ProjectCollaborator.query.filter_by(
            project_id=id,
            status=ProjectCollaborator.STATUS_ACCEPTED
        ).all()
        
        # Format collaborator data
        collaborator_data = []
        
        # Add owner as a collaborator
        owner_data = {
            'id': None,  # No collaborator record for owner
            'user_id': project.owner_id,
            'user_name': project.owner.name,
            'user_email': project.owner.email,
            'role': 'owner',
            'status': 'accepted',
            'invited_at': project.created_at.isoformat(),
            'accepted_at': project.created_at.isoformat(),
            'invited_by': None,
            'is_owner': True
        }
        collaborator_data.append(owner_data)
        
        # Add other collaborators
        for collab in collaborators:
            collab_data = {
                'id': collab.id,
                'user_id': collab.user_id,
                'user_name': collab.user.name,
                'user_email': collab.user.email,
                'role': collab.role,
                'status': collab.status,
                'invited_at': collab.invited_at.isoformat(),
                'accepted_at': collab.accepted_at.isoformat() if collab.accepted_at else None,
                'invited_by': collab.inviter.name if collab.inviter else None,
                'is_owner': False
            }
            collaborator_data.append(collab_data)
        
        return jsonify({
            'success': True,
            'project_id': id,
            'project_name': project.name,
            'collaborators': collaborator_data,
            'total_count': len(collaborator_data)
        })
    
    except Exception as e:
        return jsonify({
            'error': f'Failed to get collaborators: {str(e)}'
        }), 500


@app.route('/api/projects/<int:id>/collaborators/<int:user_id>', methods=['PUT'])
@login_required
def update_collaborator_role(id, user_id):
    """Update a collaborator's role in a project."""
    try:
        from services.permission_manager import PermissionManager
        
        # Check if user has permission to manage collaborators
        if not PermissionManager.has_permission(current_user.id, id, 'manage_collaborators'):
            return jsonify({
                'error': 'Insufficient permissions to manage collaborators'
            }), 403
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        new_role = data.get('role')
        if not new_role:
            return jsonify({'error': 'Role is required'}), 400
        
        # Validate role
        valid_roles = ['viewer', 'editor', 'admin']
        if new_role not in valid_roles:
            return jsonify({
                'error': f'Invalid role. Must be one of: {valid_roles}'
            }), 400
        
        # Check if current user can manage this role
        if not PermissionManager.can_manage_role(current_user.id, id, new_role):
            return jsonify({
                'error': f'Insufficient permissions to assign {new_role} role'
            }), 403
        
        # Get the project and check if target user is the owner
        project = Project.query.get_or_404(id)
        if project.owner_id == user_id:
            return jsonify({
                'error': 'Cannot change the role of the project owner'
            }), 400
        
        # Find the collaborator
        collaborator = ProjectCollaborator.query.filter_by(
            project_id=id,
            user_id=user_id,
            status=ProjectCollaborator.STATUS_ACCEPTED
        ).first()
        
        if not collaborator:
            return jsonify({
                'error': 'User is not a collaborator on this project'
            }), 404
        
        # Update the role
        old_role = collaborator.role
        collaborator.role = new_role
        collaborator.updated_at = datetime.utcnow()
        
        # Log the activity
        SharingActivityLog.log_activity(
            project_id=id,
            action='role_changed',
            user_id=current_user.id,
            details=f"Changed {collaborator.user.name}'s role from {old_role} to {new_role}",
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully updated {collaborator.user.name}\'s role to {new_role}',
            'collaborator': {
                'id': collaborator.id,
                'user_id': collaborator.user_id,
                'user_name': collaborator.user.name,
                'role': collaborator.role,
                'old_role': old_role,
                'updated_at': collaborator.updated_at.isoformat()
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Failed to update collaborator role: {str(e)}'
        }), 500


@app.route('/api/projects/<int:id>/collaborators/<int:user_id>', methods=['DELETE'])
@login_required
def remove_collaborator(id, user_id):
    """Remove a collaborator from a project."""
    try:
        from services.permission_manager import PermissionManager
        
        # Check if user has permission to manage collaborators
        if not PermissionManager.has_permission(current_user.id, id, 'manage_collaborators'):
            return jsonify({
                'error': 'Insufficient permissions to manage collaborators'
            }), 403
        
        # Get the project and check if target user is the owner
        project = Project.query.get_or_404(id)
        if project.owner_id == user_id:
            return jsonify({
                'error': 'Cannot remove the project owner'
            }), 400
        
        # Find the collaborator
        collaborator = ProjectCollaborator.query.filter_by(
            project_id=id,
            user_id=user_id
        ).first()
        
        if not collaborator:
            return jsonify({
                'error': 'User is not a collaborator on this project'
            }), 404
        
        # Store user info for response
        user_name = collaborator.user.name
        user_role = collaborator.role
        
        # Log the activity before deletion
        SharingActivityLog.log_activity(
            project_id=id,
            action='collaborator_removed',
            user_id=current_user.id,
            details=f"Removed {user_name} ({user_role}) from project",
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Remove the collaborator
        db.session.delete(collaborator)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully removed {user_name} from the project',
            'removed_user': {
                'user_id': user_id,
                'user_name': user_name,
                'role': user_role
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Failed to remove collaborator: {str(e)}'
        }), 500


@app.route('/api/sharing/accept/<token>', methods=['POST'])
def accept_sharing_invitation_api(token):
    """Accept a sharing invitation using a token."""
    try:
        from services.sharing_service import SharingService, InvalidTokenError, SharingServiceError
        
        # Check if user is authenticated
        if not current_user.is_authenticated:
            return jsonify({
                'error': 'Authentication required to accept invitation',
                'redirect_to_login': True,
                'token': token
            }), 401
        
        sharing_service = SharingService()
        result = sharing_service.process_sharing_token(token, current_user.id)
        
        return jsonify({
            'success': True,
            'message': result['message'],
            'project': result['project'],
            'collaborator_id': result['collaborator_id']
        })
    
    except InvalidTokenError as e:
        return jsonify({
            'error': f'Invalid or expired invitation: {str(e)}'
        }), 400
    
    except SharingServiceError as e:
        return jsonify({
            'error': str(e)
        }), 400
    
    except Exception as e:
        return jsonify({
            'error': f'Unexpected error: {str(e)}'
        }), 500


@app.route('/api/test-email', methods=['POST'])
@login_required
def test_email_sharing():
    """Test route to verify email sharing functionality"""
    try:
        from services.sharing_service import SharingService
        
        data = request.get_json()
        test_email = data.get('email', current_user.email)
        
        # Create a test project for demonstration
        test_project = type('TestProject', (), {
            'id': 1,
            'name': 'Test Project',
            'description': 'This is a test project for email sharing'
        })()
        
        sharing_service = SharingService()
        
        # Generate test sharing link
        sharing_url, token = sharing_service.generate_sharing_link(
            project_id=1,
            role='viewer',
            expires_hours=24,
            created_by=current_user.id
        )
        
        return jsonify({
            'success': True,
            'message': 'Email sharing test completed',
            'sharing_url': sharing_url,
            'test_email': test_email
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Test failed: {str(e)}'
        }), 500


@app.route('/api/projects/<int:id>/sharing/tokens', methods=['GET'])
@login_required
def get_project_sharing_tokens(id):
    """Get all active sharing tokens for a project."""
    try:
        from services.permission_manager import PermissionManager
        
        # Check if user has access to the project
        if not PermissionManager.can_access_project(current_user.id, id):
            return jsonify({
                'error': 'Access denied to this project'
            }), 403
        
        project = Project.query.get_or_404(id)
        
        # Get all active sharing tokens for this project
        tokens = SharingToken.query.filter_by(
            project_id=id,
            is_active=True
        ).order_by(SharingToken.created_at.desc()).all()
        
        # Format token data
        token_data = []
        for token in tokens:
            token_info = {
                'id': token.id,
                'token': token.token,
                'role': token.role,
                'created_at': token.created_at.isoformat(),
                'expires_at': token.expires_at.isoformat(),
                'max_uses': token.max_uses,
                'current_uses': token.current_uses,
                'is_expired': token.expires_at < datetime.utcnow(),
                'created_by_name': token.creator.name if token.creator else 'Unknown'
            }
            token_data.append(token_info)
        
        return jsonify({
            'success': True,
            'project_id': id,
            'project_name': project.name,
            'tokens': token_data,
            'total_count': len(token_data)
        })
    
    except Exception as e:
        return jsonify({
            'error': f'Failed to get sharing tokens: {str(e)}'
        }), 500


# Activity Log API Endpoints
@app.route('/api/projects/<int:project_id>/activity', methods=['GET'])
@login_required
def get_project_activity_log(project_id):
    """Get activity log for a project with filtering and pagination."""
    try:
        # Verify user has access to the project
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Check if user has access to view activity logs (owner or admin)
        if not project.is_accessible_by(current_user.id):
            return jsonify({'error': 'Access denied'}), 403
        
        user_role = project.get_user_role(current_user.id)
        if user_role not in ['owner', 'admin']:
            return jsonify({'error': 'Insufficient permissions to view activity logs'}), 403
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)  # Max 100 items per page
        action_filter = request.args.get('action')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        user_filter = request.args.get('user_id', type=int)
        
        # Build query
        query = SharingActivityLog.query.filter_by(project_id=project_id)
        
        # Apply filters
        if action_filter:
            query = query.filter(SharingActivityLog.action == action_filter)
        
        if user_filter:
            query = query.filter(SharingActivityLog.user_id == user_filter)
        
        if date_from:
            try:
                from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                query = query.filter(SharingActivityLog.created_at >= from_date)
            except ValueError:
                return jsonify({'error': 'Invalid date_from format'}), 400
        
        if date_to:
            try:
                to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                query = query.filter(SharingActivityLog.created_at <= to_date)
            except ValueError:
                return jsonify({'error': 'Invalid date_to format'}), 400
        
        # Order by most recent first
        query = query.order_by(SharingActivityLog.created_at.desc())
        
        # Paginate
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        activities = pagination.items
        
        # Serialize activities
        def serialize_activity(activity):
            user_name = None
            if activity.user_id:
                user = User.query.get(activity.user_id)
                user_name = user.name if user else f"User {activity.user_id}"
            
            return {
                'id': activity.id,
                'action': activity.action,
                'details': activity.details,
                'user_id': activity.user_id,
                'user_name': user_name,
                'ip_address': activity.ip_address,
                'user_agent': activity.user_agent,
                'created_at': activity.created_at.isoformat(),
                'is_suspicious': _is_suspicious_activity(activity)
            }
        
        return jsonify({
            'success': True,
            'activities': [serialize_activity(a) for a in activities],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'filters': {
                'action': action_filter,
                'date_from': date_from,
                'date_to': date_to,
                'user_id': user_filter
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to get activity log: {str(e)}'
        }), 500

@app.route('/api/projects/<int:project_id>/activity/export', methods=['GET'])
@login_required
def export_project_activity_log(project_id):
    """Export activity log for a project as CSV."""
    try:
        # Verify user has access to the project
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Check if user has access to export activity logs (owner or admin)
        if not project.is_accessible_by(current_user.id):
            return jsonify({'error': 'Access denied'}), 403
        
        user_role = project.get_user_role(current_user.id)
        if user_role not in ['owner', 'admin']:
            return jsonify({'error': 'Insufficient permissions to export activity logs'}), 403
        
        # Get all activities for the project
        activities = SharingActivityLog.query.filter_by(
            project_id=project_id
        ).order_by(SharingActivityLog.created_at.desc()).all()
        
        # Create CSV data
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Timestamp', 'Action', 'User', 'Details', 'IP Address', 'User Agent', 'Suspicious'
        ])
        
        # Write data
        for activity in activities:
            user_name = "System"
            if activity.user_id:
                user = User.query.get(activity.user_id)
                user_name = user.name if user else f"User {activity.user_id}"
            
            writer.writerow([
                activity.created_at.isoformat(),
                activity.action,
                user_name,
                activity.details or '',
                activity.ip_address or '',
                activity.user_agent or '',
                'Yes' if _is_suspicious_activity(activity) else 'No'
            ])
        
        # Prepare response
        from flask import make_response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=project_{project_id}_activity_log.csv'
        
        return response
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to export activity log: {str(e)}'
        }), 500

@app.route('/api/projects/<int:project_id>/activity/suspicious', methods=['GET'])
@login_required
def get_suspicious_activities(project_id):
    """Get suspicious activities for a project."""
    try:
        # Verify user has access to the project
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Check if user has access (owner or admin)
        if not project.is_accessible_by(current_user.id):
            return jsonify({'error': 'Access denied'}), 403
        
        user_role = project.get_user_role(current_user.id)
        if user_role not in ['owner', 'admin']:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        # Get recent activities (last 30 days)
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        activities = SharingActivityLog.query.filter(
            SharingActivityLog.project_id == project_id,
            SharingActivityLog.created_at >= cutoff_date
        ).order_by(SharingActivityLog.created_at.desc()).all()
        
        # Detect suspicious activities
        suspicious_activities = []
        for activity in activities:
            if _is_suspicious_activity(activity):
                user_name = None
                if activity.user_id:
                    user = User.query.get(activity.user_id)
                    user_name = user.name if user else f"User {activity.user_id}"
                
                suspicious_activities.append({
                    'id': activity.id,
                    'action': activity.action,
                    'details': activity.details,
                    'user_id': activity.user_id,
                    'user_name': user_name,
                    'ip_address': activity.ip_address,
                    'user_agent': activity.user_agent,
                    'created_at': activity.created_at.isoformat(),
                    'risk_level': _get_risk_level(activity),
                    'reason': _get_suspicious_reason(activity)
                })
        
        return jsonify({
            'success': True,
            'suspicious_activities': suspicious_activities,
            'total_count': len(suspicious_activities),
            'analysis_period': '30 days'
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to get suspicious activities: {str(e)}'
        }), 500

def _is_suspicious_activity(activity):
    """Detect if an activity is suspicious based on various criteria."""
    try:
        # Check for multiple failed access attempts from same IP
        if activity.action in ['access_denied', 'invalid_token_used']:
            recent_failures = SharingActivityLog.query.filter(
                SharingActivityLog.ip_address == activity.ip_address,
                SharingActivityLog.action.in_(['access_denied', 'invalid_token_used']),
                SharingActivityLog.created_at >= datetime.utcnow() - timedelta(hours=1)
            ).count()
            if recent_failures >= 5:
                return True
        
        # Check for unusual access patterns (e.g., access from multiple IPs in short time)
        if activity.user_id and activity.action in ['access_granted', 'project_accessed']:
            recent_ips = db.session.query(SharingActivityLog.ip_address).filter(
                SharingActivityLog.user_id == activity.user_id,
                SharingActivityLog.created_at >= datetime.utcnow() - timedelta(hours=2)
            ).distinct().count()
            if recent_ips >= 3:
                return True
        
        # Check for token usage from different IP than generation
        if activity.action == 'token_used' and activity.ip_address:
            # Find the token generation activity
            token_gen = SharingActivityLog.query.filter(
                SharingActivityLog.project_id == activity.project_id,
                SharingActivityLog.action == 'token_generated',
                SharingActivityLog.created_at <= activity.created_at
            ).order_by(SharingActivityLog.created_at.desc()).first()
            
            if (token_gen and token_gen.ip_address and 
                token_gen.ip_address != activity.ip_address):
                return True
        
        # Check for rapid successive actions (potential automation)
        if activity.user_id:
            recent_actions = SharingActivityLog.query.filter(
                SharingActivityLog.user_id == activity.user_id,
                SharingActivityLog.created_at >= datetime.utcnow() - timedelta(minutes=5)
            ).count()
            if recent_actions >= 10:
                return True
        
        return False
        
    except Exception:
        # If analysis fails, don't mark as suspicious
        return False

def _get_risk_level(activity):
    """Get risk level for suspicious activity."""
    if activity.action in ['access_denied', 'invalid_token_used']:
        return 'medium'
    elif activity.action in ['token_used', 'access_granted']:
        return 'high'
    else:
        return 'low'

def _get_suspicious_reason(activity):
    """Get reason why activity is considered suspicious."""
    reasons = []
    
    # Check for multiple failed attempts
    if activity.action in ['access_denied', 'invalid_token_used']:
        recent_failures = SharingActivityLog.query.filter(
            SharingActivityLog.ip_address == activity.ip_address,
            SharingActivityLog.action.in_(['access_denied', 'invalid_token_used']),
            SharingActivityLog.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).count()
        if recent_failures >= 5:
            reasons.append(f"Multiple failed attempts ({recent_failures}) from same IP")
    
    # Check for multiple IPs
    if activity.user_id:
        recent_ips = db.session.query(SharingActivityLog.ip_address).filter(
            SharingActivityLog.user_id == activity.user_id,
            SharingActivityLog.created_at >= datetime.utcnow() - timedelta(hours=2)
        ).distinct().count()
        if recent_ips >= 3:
            reasons.append(f"Access from multiple IPs ({recent_ips}) in short time")
    
    # Check for IP mismatch in token usage
    if activity.action == 'token_used' and activity.ip_address:
        token_gen = SharingActivityLog.query.filter(
            SharingActivityLog.project_id == activity.project_id,
            SharingActivityLog.action == 'token_generated',
            SharingActivityLog.created_at <= activity.created_at
        ).order_by(SharingActivityLog.created_at.desc()).first()
        
        if (token_gen and token_gen.ip_address and 
            token_gen.ip_address != activity.ip_address):
            reasons.append("Token used from different IP than generation")
    
    # Check for rapid actions
    if activity.user_id:
        recent_actions = SharingActivityLog.query.filter(
            SharingActivityLog.user_id == activity.user_id,
            SharingActivityLog.created_at >= datetime.utcnow() - timedelta(minutes=5)
        ).count()
        if recent_actions >= 10:
            reasons.append(f"Rapid successive actions ({recent_actions} in 5 minutes)")
    
    return "; ".join(reasons) if reasons else "Automated detection"

@app.route('/api/notifications/invitations', methods=['GET'])
@login_required
def get_invitation_notifications():
    """Get invitation notifications for the current user."""
    try:
        # Get notifications where user is the sender (for projects they own/admin)
        sent_notifications = InvitationNotification.query.filter_by(
            sender_user_id=current_user.id
        ).order_by(InvitationNotification.created_at.desc()).limit(50).all()
        
        # Get notifications where user is the recipient
        received_notifications = InvitationNotification.query.filter_by(
            recipient_user_id=current_user.id
        ).order_by(InvitationNotification.created_at.desc()).limit(50).all()
        
        def serialize_notification(notification):
            return {
                'id': notification.id,
                'project_id': notification.project_id,
                'project_name': notification.project.name if notification.project else None,
                'notification_type': notification.notification_type,
                'message': notification.message,
                'recipient_email': notification.recipient_email,
                'recipient_name': notification.recipient_user.name if notification.recipient_user else None,
                'sender_name': notification.sender_user.name if notification.sender_user else None,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat(),
                'read_at': notification.read_at.isoformat() if notification.read_at else None
            }
        
        return jsonify({
            'success': True,
            'sent_notifications': [serialize_notification(n) for n in sent_notifications],
            'received_notifications': [serialize_notification(n) for n in received_notifications]
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to get notifications: {str(e)}'
        }), 500

@app.route('/api/notifications/invitations/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_invitation_notification_read(notification_id):
    """Mark an invitation notification as read."""
    try:
        notification = InvitationNotification.query.get(notification_id)
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        # Check if user has permission to mark this notification as read
        if (notification.sender_user_id != current_user.id and 
            notification.recipient_user_id != current_user.id):
            return jsonify({'error': 'Access denied'}), 403
        
        notification.mark_as_read()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Notification marked as read'
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to mark notification as read: {str(e)}'
        }), 500

# Process pending sharing token after login
# Removed process_pending_sharing_token - now handled directly in OAuth callbacks

def create_tables():
    """Create database tables if they don't exist"""
    try:
        with app.app_context():
            db.create_all()
            print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        # Don't raise - let the app continue

# Security enhancements are handled by Azure security config
print("Security enhancements configured via Azure security config")

if __name__ == '__main__':
    create_tables()
    # Use SocketIO run instead of app.run for WebSocket support
    port = int(os.environ.get('PORT', 5000))  # Changed default to 5000
    socketio.run(app, debug=True, host='0.0.0.0', port=port)

@app.route('/health')
def health_check():
    """Health check endpoint for Azure monitoring"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'services': {}
        }
        
        # Check database connectivity
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            health_status['services']['database'] = 'healthy'
        except Exception as e:
            health_status['services']['database'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Check Azure services if available
        try:
            if hasattr(app, 'azure_services_manager'):
                from services.azure_services_config import get_azure_services_status
                azure_status = get_azure_services_status()
                health_status['services']['azure'] = {
                    'enabled_services': azure_status.get('enabled_services', []),
                    'overall_status': azure_status.get('overall_status', 'unknown')
                }
        except Exception as e:
            health_status['services']['azure'] = f'error: {str(e)}'
        
        # Check WebSocket handler
        try:
            if ws_handler:
                active_connections = len(ws_handler.active_connections)
                health_status['services']['websocket'] = f'healthy (connections: {active_connections})'
            else:
                health_status['services']['websocket'] = 'not_initialized'
        except Exception as e:
            health_status['services']['websocket'] = f'error: {str(e)}'
        
        # Determine overall status
        unhealthy_services = [k for k, v in health_status['services'].items() 
                            if isinstance(v, str) and ('unhealthy' in v or 'error' in v)]
        
        if unhealthy_services:
            if 'database' in unhealthy_services:
                health_status['status'] = 'unhealthy'
            else:
                health_status['status'] = 'degraded'
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@app.route('/api/azure/status')
@login_required
def azure_services_status():
    """Get Azure services status (admin only)"""
    try:
        # Check if user is admin (you may want to implement proper admin check)
        if not current_user.email.endswith('@admin.com'):  # Replace with your admin logic
            return jsonify({'error': 'Unauthorized'}), 403
        
        from services.azure_services_config import get_azure_services_status
        
        # Get services status
        services_status = get_azure_services_status()
        
        return jsonify({
            'services_status': services_status,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting Azure services status: {e}")
        return jsonify({
            'error': 'Failed to get Azure services status',
            'details': str(e)
        }), 500