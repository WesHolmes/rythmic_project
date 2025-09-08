from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import pandas as pd
import io
import csv
from authlib.integrations.flask_client import OAuth
from ai_service import AIAssistant

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration - use environment variable or default to SQLite
database_url = os.environ.get('DATABASE_URL', 'sqlite:///rhythmic.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

microsoft = oauth.register(
    name='microsoft',
    client_id=os.environ.get('OUTLOOK_CLIENT_ID'),
    client_secret=os.environ.get('OUTLOOK_CLIENT_SECRET'),
    server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid_configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(128))
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

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

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
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# OAuth Routes
@app.route('/login/google')
def login_google():
    redirect_uri = url_for('authorize_google', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/microsoft')
def login_microsoft():
    redirect_uri = url_for('authorize_microsoft', _external=True)
    return microsoft.authorize_redirect(redirect_uri)

@app.route('/authorize/google')
def authorize_google():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if user_info:
            email = user_info.get('email')
            name = user_info.get('name', email.split('@')[0])
            provider_id = user_info.get('sub')
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
            return redirect(url_for('index'))
        else:
            flash('Failed to get user information from Google')
            return redirect(url_for('login'))
    except Exception as e:
        flash(f'Google authentication failed: {str(e)}')
        return redirect(url_for('login'))

@app.route('/authorize/microsoft')
def authorize_microsoft():
    try:
        token = microsoft.authorize_access_token()
        user_info = token.get('userinfo')
        
        if user_info:
            email = user_info.get('email')
            name = user_info.get('name', email.split('@')[0])
            provider_id = user_info.get('sub')
            avatar_url = None  # Microsoft doesn't provide avatar in basic scope
            
            # Check if user exists
            user = User.query.filter_by(email=email, provider='microsoft').first()
            
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
                    provider='microsoft',
                    provider_id=provider_id,
                    avatar_url=avatar_url
                )
                db.session.add(user)
                db.session.commit()
            
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Failed to get user information from Microsoft')
            return redirect(url_for('login'))
    except Exception as e:
        flash(f'Microsoft authentication failed: {str(e)}')
        return redirect(url_for('login'))

@app.route('/projects')
@login_required
def projects():
    projects = Project.query.filter_by(owner_id=current_user.id).all()
    return render_template('projects.html', projects=projects)

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
    project = Project.query.get_or_404(id)
    if project.owner_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('projects'))
    
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
    
    return render_template('project_detail.html', project=project, tasks=tasks, tasks_data=tasks_data, labels=labels)

@app.route('/projects/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(id):
    project = Project.query.get_or_404(id)
    if project.owner_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('projects'))
    
    if request.method == 'POST':
        project.name = request.form['name']
        project.description = request.form['description']
        project.vision = request.form.get('vision', '')
        project.problems = request.form.get('problems', '')
        project.timeline = request.form.get('timeline', '')
        project.impact = request.form.get('impact', '')
        project.goals = request.form.get('goals', '')
        db.session.commit()
        return redirect(url_for('view_project', id=id))
    
    return render_template('edit_project.html', project=project)

@app.route('/projects/<int:id>/delete', methods=['POST'])
@login_required
def delete_project(id):
    project = Project.query.get_or_404(id)
    if project.owner_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('projects'))
    
    db.session.delete(project)
    db.session.commit()
    return redirect(url_for('projects'))

# Task routes
@app.route('/projects/<int:project_id>/tasks/new', methods=['GET', 'POST'])
@login_required
def new_task(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('projects'))
    
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
        
        db.session.commit()
        return redirect(url_for('view_project', id=project_id))
    
    # Get existing tasks for parent selection and labels for selection
    tasks = Task.query.filter_by(project_id=project_id).all()
    labels = Label.query.filter_by(project_id=project_id).all()
    return render_template('new_task.html', project=project, tasks=tasks, labels=labels)

@app.route('/projects/<int:project_id>/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(project_id, task_id):
    project = Project.query.get_or_404(project_id)
    task = Task.query.get_or_404(task_id)
    
    if project.owner_id != current_user.id or task.project_id != project_id:
        flash('Access denied')
        return redirect(url_for('projects'))
    
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
        
        # Handle labels - remove existing and add new ones
        TaskLabel.query.filter_by(task_id=task_id).delete()
        label_ids = request.form.getlist('labels')
        for label_id in label_ids:
            if label_id:  # Skip empty values
                task_label = TaskLabel(task_id=task_id, label_id=int(label_id))
                db.session.add(task_label)
        
        db.session.commit()
        return redirect(url_for('view_project', id=project_id))
    
    tasks = Task.query.filter_by(project_id=project_id).filter(Task.id != task_id).all()
    labels = Label.query.filter_by(project_id=project_id).all()
    return render_template('edit_task.html', project=project, task=task, tasks=tasks, labels=labels)

@app.route('/projects/<int:project_id>/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(project_id, task_id):
    project = Project.query.get_or_404(project_id)
    task = Task.query.get_or_404(task_id)
    
    if project.owner_id != current_user.id or task.project_id != project_id:
        flash('Access denied')
        return redirect(url_for('projects'))
    
    db.session.delete(task)
    db.session.commit()
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
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
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
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
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
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
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
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
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
    project = Project.query.get_or_404(project_id)
    task = Task.query.get_or_404(task_id)
    
    if project.owner_id != current_user.id or task.project_id != project_id:
        return jsonify({'error': 'Access denied'}), 403
    
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
    project = Project.query.get_or_404(project_id)
    task = Task.query.get_or_404(task_id)
    
    if project.owner_id != current_user.id or task.project_id != project_id:
        return jsonify({'error': 'Access denied'}), 403
    
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
    try:
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
    try:
        project = Project.query.get_or_404(project_id)
        if project.owner_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
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
    try:
        project = Project.query.get_or_404(project_id)
        task = Task.query.get_or_404(task_id)
        
        if project.owner_id != current_user.id or task.project_id != project_id:
            return jsonify({'error': 'Access denied'}), 403
        
        task.is_expanded = not task.is_expanded
        db.session.commit()
        
        return jsonify({'is_expanded': task.is_expanded})
        
    except Exception as e:
        return jsonify({'error': f'Failed to toggle task expansion: {str(e)}'}), 500

@app.route('/api/projects/<int:project_id>/tasks/<int:task_id>/dependencies', methods=['POST'])
@login_required
def add_task_dependency(project_id, task_id):
    """Add a dependency to a task"""
    try:
        project = Project.query.get_or_404(project_id)
        task = Task.query.get_or_404(task_id)
        
        if project.owner_id != current_user.id or task.project_id != project_id:
            return jsonify({'error': 'Access denied'}), 403
        
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
    try:
        project = Project.query.get_or_404(project_id)
        task = Task.query.get_or_404(task_id)
        
        if project.owner_id != current_user.id or task.project_id != project_id:
            return jsonify({'error': 'Access denied'}), 403
        
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
