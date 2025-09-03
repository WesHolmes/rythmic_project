from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv
import pandas as pd
import io
import csv
from authlib.integrations.flask_client import OAuth

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rhythmic.db'
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
    
    # Relationships
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = db.relationship('User', backref='tasks')
    children = db.relationship('Task', backref=db.backref('parent', remote_side=[id]), lazy=True)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        projects = Project.query.filter_by(owner_id=current_user.id).all()
        return render_template('dashboard.html', projects=projects)
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
            owner_id=current_user.id
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
    
    # Get tasks with hierarchy
    tasks = Task.query.filter_by(project_id=id).all()
    
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
            'owner_name': task.owner.name if task.owner else 'Unknown'
        }
        tasks_data.append(task_dict)
    
    return render_template('project_detail.html', project=project, tasks=tasks, tasks_data=tasks_data)

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
            parent_id=int(request.form['parent_id']) if request.form['parent_id'] else None
        )
        db.session.add(task)
        db.session.commit()
        return redirect(url_for('view_project', id=project_id))
    
    # Get existing tasks for parent selection
    tasks = Task.query.filter_by(project_id=project_id).all()
    return render_template('new_task.html', project=project, tasks=tasks)

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
        db.session.commit()
        return redirect(url_for('view_project', id=project_id))
    
    tasks = Task.query.filter_by(project_id=project_id).filter(Task.id != task_id).all()
    return render_template('edit_task.html', project=project, task=task, tasks=tasks)

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
