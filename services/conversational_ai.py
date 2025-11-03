"""
Conversational AI Service for Rhythmic

Provides intelligent, context-aware AI assistance that understands the entire application
and respects user permissions.
"""
#for ai chat
import os
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from openai import OpenAI
from flask_login import current_user
import httpx


class ConversationalAI:
    """Intelligent AI assistant with full application context"""
    
    def __init__(self):
        api_key = os.environ.get('OPENAI_API_KEY')
        model = os.environ.get('AI_MODEL', 'gpt-4o')  # Default to GPT-4o, fallback to gpt-3.5-turbo
        
        if not api_key:
            print("⚠️  OPENAI_API_KEY not found. AI features will use fallback responses.")
            self.client = None
            self.model = 'fallback'
        else:
            try:
                # Create a clean httpx client without proxy settings to avoid conflicts
                # This works around an issue where the OpenAI library tries to pass
                # proxy settings that httpx doesn't accept in this version
                http_client = httpx.Client(timeout=60.0)
                self.client = OpenAI(api_key=api_key, http_client=http_client)
                self.model = model
            except Exception as e:
                print(f"⚠️  Failed to initialize OpenAI client: {e}. Using fallback responses.")
                self.client = None
                self.model = 'fallback'
        
        # Application knowledge base
        self.app_knowledge = self._load_app_knowledge()
    
    def _load_app_knowledge(self) -> str:
        """Load knowledge about the application"""
        return """
Rhythmic is a comprehensive project management application with the following features:

CORE FEATURES:
1. Projects: Create and manage multiple projects with descriptions and metadata
2. Tasks: Hierarchical task management with unlimited nesting levels
3. Workflow States: Tasks progress through: backlog → in_progress → committed → completed
4. Task Assignment: Assign tasks to team members with notification system
5. Task Dependencies: Link tasks to show prerequisites and relationships
6. Labels: Custom labels for task categorization with colors
7. Task Flagging: Flag tasks for clarification or attention
8. Sharing & Collaboration: Role-based access control (owner, admin, editor, viewer)
9. Activity Log: Track all changes and events in real-time
10. Export/Import: Export projects to JSON or import from templates

PERMISSION SYSTEM:
- Owner: Full control over the project
- Admin: Can edit project, manage collaborators, assign tasks
- Editor: Can create and edit tasks
- Viewer: Read-only access

TASK PROPERTIES:
- Title and description
- Start and end dates
- Status (backlog, in_progress, committed, completed)
- Workflow status
- Priority (low, medium, high)
- Size (small, medium, large)
- Risk level (low, medium, high, critical)
- Assigned to team members
- Parent-child relationships (hierarchical)
- Dependencies on other tasks
- Labels for categorization
- Flagging for attention
"""
    
    def build_user_context(self, user) -> Dict:
        """Build comprehensive context for the user"""
        # Import here to avoid circular imports
        try:
            from app import Project, Task, ProjectCollaborator, db
        except ImportError:
            # Fallback for when running in different contexts
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            from app import Project, Task, ProjectCollaborator, db
        
        # Get all projects user has access to
        try:
            user_owned_projects = Project.query.filter_by(owner_id=user.id).all()
        except Exception as e:
            print(f"Error querying owned projects: {e}")
            user_owned_projects = []
        
        # Get collaborated projects
        try:
            collaborations = ProjectCollaborator.query.filter_by(
                user_id=user.id,
                status=ProjectCollaborator.STATUS_ACCEPTED
            ).all()
            user_collaborated_projects = [Project.query.get(collab.project_id) for collab in collaborations if collab]
        except Exception as e:
            print(f"Error querying collaborations: {e}")
            user_collaborated_projects = []
        
        all_user_projects = list(user_owned_projects) + user_collaborated_projects
        all_project_ids = [p.id for p in all_user_projects]
        
        # Get all user-accessible tasks
        try:
            all_tasks = Task.query.filter(Task.project_id.in_(all_project_ids)).all() if all_project_ids else []
        except Exception as e:
            print(f"Error querying tasks: {e}")
            all_tasks = []
        
        # Build project summary
        projects_data = []
        for project in all_user_projects:
            role = 'owner' if project.owner_id == user.id else project.get_user_role(user.id)
            project_tasks = [t for t in all_tasks if t.project_id == project.id]
            
            projects_data.append({
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'role': role,
                'task_count': len(project_tasks),
                'completed_tasks': len([t for t in project_tasks if t.status == 'completed']),
                'in_progress_tasks': len([t for t in project_tasks if t.workflow_status == 'in_progress']),
                'overdue_tasks': self._count_overdue_tasks(project_tasks),
                'vision': project.vision,
                'goals': project.goals,
                'created_at': project.created_at.isoformat() if project.created_at else None
            })
        
        # Get stale tasks (not updated in 30+ days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        stale_tasks = [
            t for t in all_tasks 
            if t.status != 'completed' 
            and t.workflow_status != 'completed'
            and t.updated_at 
            and t.updated_at < thirty_days_ago
        ]
        
        # Get at-risk tasks (due within 7 days or overdue)
        now = datetime.utcnow()
        at_risk_tasks = []
        for task in all_tasks:
            if task.status != 'completed' and task.workflow_status != 'completed' and task.end_date:
                days_until_due = (task.end_date - now.date()).days
                if days_until_due <= 7:
                    at_risk_tasks.append({
                        'title': task.title,
                        'project_id': task.project_id,
                        'days_until_due': days_until_due,
                        'is_overdue': days_until_due < 0
                    })
        
        # Build task statistics
        task_stats = {
            'total': len(all_tasks),
            'completed': len([t for t in all_tasks if t.status == 'completed']),
            'in_progress': len([t for t in all_tasks if t.workflow_status == 'in_progress']),
            'backlog': len([t for t in all_tasks if t.workflow_status == 'backlog']),
            'committed': len([t for t in all_tasks if t.workflow_status == 'committed']),
            'assigned_to_me': len([t for t in all_tasks if t.assigned_to == user.id]),
            'flagged': len([t for t in all_tasks if t.is_flagged]),
            'stale': len(stale_tasks),
            'at_risk': len(at_risk_tasks)
        }
        
        return {
            'user_name': user.name,
            'projects': projects_data,
            'task_stats': task_stats,
            'stale_tasks': [{'title': t.title, 'project_id': t.project_id} for t in stale_tasks[:10]],
            'at_risk_tasks': at_risk_tasks[:10],
            'current_time': now.isoformat()
        }
    
    def _count_overdue_tasks(self, tasks: List) -> int:
        """Count tasks that are overdue"""
        now = datetime.utcnow()
        overdue_count = 0
        for task in tasks:
            if task.end_date and task.status != 'completed':
                if task.end_date < now.date():
                    overdue_count += 1
        return overdue_count
    
    def generate_response(self, user_message: str, context: Dict) -> str:
        """Generate intelligent response using OpenAI"""
        
        if not self.client:
            return self._generate_fallback_response(user_message, context)
        
        # Build system prompt with context
        system_prompt = f"""You are an AI assistant for Rhythmic, a powerful project management application.

APPLICATION KNOWLEDGE:
{self.app_knowledge}

USER CONTEXT:
Username: {context['user_name']}

PROJECTS ({len(context['projects'])} total):
{json.dumps(context['projects'], indent=2)}

TASK STATISTICS:
{json.dumps(context['task_stats'], indent=2)}

STALE TASKS ({len(context['stale_tasks'])}): Tasks not updated in 30+ days
{json.dumps(context['stale_tasks'][:5], indent=2)}

AT-RISK TASKS ({len(context['at_risk_tasks'])}): Due within 7 days or overdue
{json.dumps(context['at_risk_tasks'][:5], indent=2)}

RESPONSE GUIDELINES:
1. Be conversational, helpful, and concise
2. Provide specific, actionable advice based on user's actual data
3. Use formatting: Use HTML for rich responses (<h4>, <ul>, <li>, <p>, <strong>)
4. For lists, use <ul class="list-disc list-inside space-y-1 text-sm"> and <li> tags
5. For headings, use <h4 class="text-blue-400 mb-2">
6. For warnings, use <h4 class="text-orange-400 mb-2">
7. For success, use <h4 class="text-green-400 mb-2">
8. Only suggest actions the user has permission to perform
9. If asked about something you don't know, say "I don't have that information in your current projects, but I can help you..."
10. When mentioning projects or tasks, be specific with names/IDs

RESPONSE FORMAT:
- Use HTML for formatting
- Keep responses concise but informative
- Include actionable suggestions when relevant"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._generate_fallback_response(user_message, context)
    
    def _generate_fallback_response(self, user_message: str, context: Dict) -> str:
        """Generate fallback response when OpenAI is unavailable"""
        message_lower = user_message.lower()
        
        # Check for specific intents
        if any(word in message_lower for word in ['project', 'projects']):
            if context['projects']:
                project_list = '\n'.join([
                    f"<li><strong>{p['name']}</strong> - {p['task_count']} tasks, {p['completed_tasks']} completed</li>"
                    for p in context['projects']
                ])
                return f"""
<h4 class="text-blue-400 mb-2">Your Projects:</h4>
<ul class="list-disc list-inside space-y-1 text-sm">{project_list}</ul>
<p class="text-sm mt-2">You have {len(context['projects'])} project(s) in total.</p>
"""
            else:
                return """
<h4 class="text-blue-400 mb-2">No Projects Yet</h4>
<p class="text-sm">You don't have any projects yet. Click "New Project" to create your first project!</p>
"""
        
        elif any(word in message_lower for word in ['task', 'tasks', 'to-do']):
            stats = context['task_stats']
            return f"""
<h4 class="text-blue-400 mb-2">Your Task Overview:</h4>
<ul class="list-disc list-inside space-y-1 text-sm">
    <li>Total tasks: {stats['total']}</li>
    <li>Completed: {stats['completed']}</li>
    <li>In progress: {stats['in_progress']}</li>
    <li>Backlog: {stats['backlog']}</li>
    <li>Assigned to you: {stats['assigned_to_me']}</li>
</ul>
<p class="text-sm mt-2">You have {stats['stale']} stale tasks and {stats['at_risk']} at-risk tasks.</p>
"""
        
        elif any(word in message_lower for word in ['stale', 'old', 'forgotten']):
            stale = context['stale_tasks']
            if stale:
                task_list = '\n'.join([f"<li><strong>{t['title']}</strong></li>" for t in stale[:5]])
                return f"""
<h4 class="text-orange-400 mb-2">⚠️ Stale Tasks:</h4>
<p class="text-sm mb-2">You have {len(stale)} task(s) not updated in 30+ days:</p>
<ul class="list-disc list-inside space-y-1 text-sm">{task_list}</ul>
"""
            else:
                return """
<h4 class="text-green-400 mb-2">✅ No Stale Tasks!</h4>
<p class="text-sm">Great job keeping everything up to date!</p>
"""
        
        elif any(word in message_lower for word in ['overdue', 'late', 'due', 'at risk']):
            at_risk = context['at_risk_tasks']
            if at_risk:
                task_list = '\n'.join([
                    f"<li><strong>{t['title']}</strong> - {abs(t['days_until_due'])} days {'overdue' if t['is_overdue'] else 'remaining'}</li>"
                    for t in at_risk[:5]
                ])
                return f"""
<h4 class="text-orange-400 mb-2">⚠️ At-Risk Tasks:</h4>
<p class="text-sm mb-2">You have {len(at_risk)} task(s) due within 7 days or overdue:</p>
<ul class="list-disc list-inside space-y-1 text-sm">{task_list}</ul>
"""
            else:
                return """
<h4 class="text-green-400 mb-2">✅ No At-Risk Tasks!</h4>
<p class="text-sm">All your tasks are on track!</p>
"""
        
        else:
            return """
<h4 class="text-blue-400 mb-2">I'd be happy to help!</h4>
<p class="text-sm mb-2">Here are some things I can help with:</p>
<ul class="list-disc list-inside space-y-1 text-sm">
    <li>Tell you about your projects and tasks</li>
    <li>Show stale or overdue tasks</li>
    <li>Provide project insights and recommendations</li>
    <li>Help you organize your workload</li>
</ul>
<p class="text-sm mt-2">Try asking: "show me my projects" or "what tasks need attention"</p>
"""

