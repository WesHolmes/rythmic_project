# Rhythmic Project Management

A Flask-based project management application that helps teams establish effective project rhythm and manage tasks collaboratively.

## Features

- **User Authentication**: Secure login and registration system
- **Project Management**: Create, edit, and manage projects
- **Task Management**: Hierarchical task organization with status tracking
- **Timeline View**: Visual timeline of project tasks and milestones
- **CSV Import/Export**: Import existing project data and export for archiving
- **Responsive Design**: Works on desktop and mobile devices

## Technology Stack

- **Backend**: Python 3, Flask, SQLAlchemy
- **Database**: SQLite3
- **Frontend**: HTML5, CSS3, JavaScript, Tailwind CSS
- **Authentication**: Flask-Login with password hashing

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd rhythmic-project
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser and go to `http://localhost:5000`

## Usage

### Getting Started

1. **Register an account** or **login** with existing credentials
2. **Create your first project** by clicking "New Project"
3. **Add tasks** to your project with details like:
   - Title and description
   - Start and end dates
   - Status (backlog, committed, in progress, blocked, completed)
   - Priority (low, medium, high)
   - Size (small, medium, large)
   - Parent task (for hierarchical organization)

### Key Features

- **Dashboard**: View all your projects in one place
- **Project Detail**: Manage tasks within a project
- **Timeline View**: Visual representation of project timeline
- **CSV Import/Export**: Bulk import tasks or export for backup
- **Task Hierarchy**: Organize tasks with parent-child relationships

## Project Structure

```
rhythmic-project/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── env.example           # Environment variables template
├── templates/            # HTML templates
│   ├── base.html
│   ├── landing.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── projects.html
│   ├── new_project.html
│   ├── project_detail.html
│   ├── edit_project.html
│   ├── new_task.html
│   ├── edit_task.html
│   └── import_project.html
├── static/               # Static assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── README.md
```

## Database Schema

### Users
- id (Primary Key)
- email (Unique)
- name
- password_hash
- created_at

### Projects
- id (Primary Key)
- name
- description
- owner_id (Foreign Key to Users)
- created_at
- updated_at

### Tasks
- id (Primary Key)
- title
- description
- project_id (Foreign Key to Projects)
- owner_id (Foreign Key to Users)
- start_date
- end_date
- status
- priority
- size
- parent_id (Foreign Key to Tasks for hierarchy)
- created_at
- updated_at

## Development

### Running in Development Mode

```bash
export FLASK_ENV=development
export FLASK_DEBUG=True
python app.py
```

### Database Operations

The database is automatically created when you first run the application. To reset the database:

```bash
rm rhythmic.db
python app.py
```

## Future Enhancements

- OAuth integration with Google/Outlook
- Real-time collaboration features
- Advanced reporting and analytics
- AI-powered project planning assistance
- Team member invitations and permissions
- Advanced timeline and Gantt chart views

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.
