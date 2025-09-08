# Rhythmic Project Manager

A modern, AI-powered project management application built with Flask. Organize your projects, manage tasks with advanced features like dependencies and risk assessment, and leverage AI assistance for project planning.

## 🚀 Features

### Core Project Management
- **Project Creation & Management** - Create, edit, and organize your projects
- **Task Management** - Add, edit, and track tasks with hierarchical structure
- **Advanced Task Features**:
  - Task dependencies (finish-to-start, start-to-start, etc.)
  - Risk assessment and mitigation planning
  - Priority and size management
  - Drag-and-drop reordering
  - Label system with custom colors and icons

### AI-Powered Features
- **Project Brief Generation** - AI creates comprehensive project briefs from your ideas
- **Starter Task Generation** - Automatically generate initial tasks for your projects
- **Project Summaries** - AI-generated project overviews and insights

### User Management
- **Multiple Authentication Options**:
  - Local registration/login
  - Google OAuth
  - Microsoft OAuth
- **User-specific Projects** - Each user manages their own project portfolio

### Data Management
- **CSV Import/Export** - Bulk import/export tasks via CSV files
- **Project Templates** - Reusable project structures
- **Advanced Filtering** - Filter tasks by status, priority, labels, and more

## 🛠️ Technology Stack

- **Backend**: Flask (Python 3.11+)
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: HTML5, Tailwind CSS, JavaScript
- **AI Integration**: OpenAI GPT API
- **Authentication**: Flask-Login, OAuth (Google, Microsoft)
- **Deployment**: Azure App Service ready

## 📋 Prerequisites

- Python 3.11 or higher
- OpenAI API key (for AI features)
- Google/Microsoft OAuth credentials (optional, for social login)

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd rhythmic-project-manager
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
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

6. **Open your browser**
   Navigate to `http://localhost:5000`

### Environment Variables

Create a `.env` file with the following variables:

```env
# Required
SECRET_KEY=your-super-secret-key-here
OPENAI_API_KEY=your-openai-api-key

# Optional (for OAuth)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
OUTLOOK_CLIENT_ID=your-microsoft-client-id
OUTLOOK_CLIENT_SECRET=your-microsoft-client-secret

# Database (optional, defaults to SQLite)
DATABASE_URL=sqlite:///rhythmic.db
```

## 🌐 Azure Deployment

This application is ready for Azure App Service deployment.

### Prerequisites
- Azure subscription
- Azure CLI (optional)

### Deployment Steps

1. **Create Azure App Service**
   - Runtime: Python 3.11
   - Operating System: Linux

2. **Configure Environment Variables**
   In Azure Portal → App Service → Configuration → Application settings:
   ```
   SECRET_KEY = your-secret-key
   OPENAI_API_KEY = your-openai-key
   ```

3. **Deploy via Git**
   ```bash
   git remote add azure https://yourapp.scm.azurewebsites.net/yourapp.git
   git push azure main
   ```

4. **Monitor Deployment**
   Check logs in Azure Portal → App Service → Log stream

For detailed deployment instructions, see [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md).

## 📖 Usage Guide

### Creating Your First Project

1. **Register/Login** - Create an account or sign in
2. **Create Project** - Click "New Project" and fill in details
3. **Add Tasks** - Start adding tasks to your project
4. **Use AI Features** - Generate project briefs and starter tasks
5. **Organize** - Use labels, dependencies, and priorities to organize

### AI Features

- **Project Brief**: Enter your project idea and get a comprehensive brief
- **Starter Tasks**: Generate initial tasks based on your project description
- **Smart Summaries**: Get AI-generated project insights

### Advanced Task Management

- **Dependencies**: Link tasks that depend on each other
- **Risk Assessment**: Identify and plan for potential risks
- **Labels**: Categorize tasks with custom labels
- **Hierarchy**: Create parent-child task relationships

## 🔧 Development

### Project Structure
```
rhythmic-project-manager/
├── app.py                 # Main Flask application
├── ai_service.py         # AI integration service
├── templates/            # HTML templates
├── static/              # CSS, JS, images
├── requirements.txt     # Python dependencies
├── startup.py          # Azure startup script
├── web.config          # Azure IIS configuration
└── README.md           # This file
```

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=app
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🔒 Security

- Environment variables for sensitive data
- CSRF protection with Flask-WTF
- Secure password hashing
- OAuth integration for secure authentication
- Input validation and sanitization

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

- **Issues**: Report bugs and request features via GitHub Issues
- **Documentation**: Check the [project wiki](../../wiki) for detailed guides
- **Community**: Join our discussions in GitHub Discussions

## 🎯 Roadmap

- [ ] Team collaboration features
- [ ] Mobile app
- [ ] Advanced reporting and analytics
- [ ] Integration with external tools (Slack, Trello, etc.)
- [ ] Custom project templates
- [ ] Time tracking
- [ ] Gantt chart visualization

## 🙏 Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- UI powered by [Tailwind CSS](https://tailwindcss.com/)
- AI features by [OpenAI](https://openai.com/)
- Icons by [Font Awesome](https://fontawesome.com/)

---

**Made with ❤️ for better project management**