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
    
    def _format_timestamp(self, timestamp_str: Optional[str]) -> Optional[str]:
        """Format ISO timestamp to human-friendly format (relative time for recent, absolute for older)"""
        if not timestamp_str:
            return None
        
        try:
            # Parse the timestamp
            if 'Z' in timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(timestamp_str)
            
            # Get current time - make timezone-aware if needed
            from datetime import timezone
            if dt.tzinfo:
                # Timestamp is timezone-aware, use timezone-aware now
                now = datetime.now(timezone.utc)
            else:
                # Timestamp is naive, use naive now
                now = datetime.utcnow()
            
            # Calculate difference (both should be same type now)
            diff = now - dt
            
            # Less than a minute ago
            if diff.total_seconds() < 60:
                return "just now"
            
            # Less than an hour ago
            if diff.total_seconds() < 3600:
                minutes = int(diff.total_seconds() / 60)
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            
            # Less than 24 hours ago
            if diff.total_seconds() < 86400:
                hours = int(diff.total_seconds() / 3600)
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            
            # Less than 7 days ago
            if diff.days < 7:
                return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
            
            # Less than 30 days ago
            if diff.days < 30:
                weeks = diff.days // 7
                return f"{weeks} week{'s' if weeks != 1 else ''} ago"
            
            # For older timestamps, return absolute date format
            # Format as "Month Day, Year" (e.g., "November 13, 2025")
            return dt.strftime("%B %d, %Y")
            
        except Exception as e:
            print(f"Error formatting timestamp {timestamp_str}: {e}")
            return timestamp_str
    
    def _format_date(self, date_obj) -> Optional[str]:
        """Format a date object to human-readable format (e.g., 'November 13, 2025')"""
        if not date_obj:
            return None
        
        try:
            if isinstance(date_obj, str):
                # If it's already a string, try to parse it
                if 'T' in date_obj or ' ' in date_obj:
                    # It's a datetime string
                    dt = datetime.fromisoformat(date_obj.replace('Z', '+00:00') if 'Z' in date_obj else date_obj)
                    return dt.strftime("%B %d, %Y")
                else:
                    # It's a date string
                    from datetime import date as date_type
                    d = date_type.fromisoformat(date_obj)
                    return d.strftime("%B %d, %Y")
            elif hasattr(date_obj, 'isoformat'):
                # It's a date or datetime object
                if hasattr(date_obj, 'hour'):
                    # It's a datetime
                    return date_obj.strftime("%B %d, %Y")
                else:
                    # It's a date
                    return date_obj.strftime("%B %d, %Y")
            else:
                return str(date_obj)
        except Exception as e:
            print(f"Error formatting date {date_obj}: {e}")
            return str(date_obj) if date_obj else None
    
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
    
    def build_user_context(self, user, project_id: Optional[int] = None) -> Dict:
        """Build comprehensive context for the user with full database access respecting role permissions.
        
        Args:
            user: The current user
            project_id: Optional project ID to filter context to a specific project
        """
        # Set current time at the very start to ensure consistency
        now = datetime.utcnow()
        
        # Import here to avoid circular imports
        try:
            from app import Project, Task, ProjectCollaborator, User, Label, TaskDependency, db
        except ImportError:
            # Fallback for when running in different contexts
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            from app import Project, Task, ProjectCollaborator, User, Label, TaskDependency, db
        
        # Expire all objects in the session to force fresh queries
        # This ensures we get the latest data from the database
        try:
            db.session.expire_all()
        except Exception as e:
            print(f"Warning: Could not expire session: {e}")
        
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
        
        # Filter to specific project if provided
        if project_id:
            all_user_projects = [p for p in all_user_projects if p.id == project_id]
            if not all_user_projects:
                # User doesn't have access to this project
                return {
                    'user_name': user.name,
                    'user_id': user.id,
                    'projects': [],
                    'tasks': [],
                    'task_stats': {},
                    'stale_tasks': [],
                    'at_risk_tasks': [],
                    'current_time': datetime.utcnow().isoformat(),
                    'current_project_id': project_id
                }
        
        all_project_ids = [p.id for p in all_user_projects]
        
        # Get all user-accessible tasks with relationships loaded
        # Query fresh from database to ensure we have the latest tracking data
        try:
            if all_project_ids:
                # Use with_for_update(False) to ensure we get fresh data, or just query normally
                # The expire_all() above should ensure fresh data, but we'll also merge to be safe
                all_tasks = Task.query.filter(Task.project_id.in_(all_project_ids)).all()
                # Force refresh by accessing the attributes (this will query fresh if expired)
                for task in all_tasks:
                    # Access tracking fields to ensure they're loaded fresh
                    _ = task.task_last_read_date
                    _ = task.task_last_read_user
                    _ = task.task_last_update_user
            else:
                all_tasks = []
        except Exception as e:
            print(f"Error querying tasks: {e}")
            all_tasks = []
        
        # Build a user lookup map for assigned users
        user_lookup = {}
        try:
            all_user_ids = set()
            for task in all_tasks:
                if task.assigned_to:
                    all_user_ids.add(task.assigned_to)
                if task.assigned_by:
                    all_user_ids.add(task.assigned_by)
                if task.flagged_by:
                    all_user_ids.add(task.flagged_by)
                if task.flag_resolved_by:
                    all_user_ids.add(task.flag_resolved_by)
            
            users = User.query.filter(User.id.in_(all_user_ids)).all() if all_user_ids else []
            user_lookup = {u.id: u.name for u in users}
        except Exception as e:
            print(f"Error building user lookup: {e}")
        
        # Build project summary with role-based field access
        projects_data = []
        for project in all_user_projects:
            role = 'owner' if project.owner_id == user.id else project.get_user_role(user.id)
            project_tasks = [t for t in all_tasks if t.project_id == project.id]
            
            # Base project data (all roles can see)
            project_data = {
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
                'created_at': self._format_timestamp(project.created_at.isoformat() if project.created_at else None)
            }
            
            # Add admin/owner-only fields
            if role in ['owner', 'admin']:
                project_data.update({
                    'problems': project.problems,
                    'timeline': project.timeline,
                    'impact': project.impact,
                    'updated_at': self._format_timestamp(project.updated_at.isoformat() if project.updated_at else None)
                })
            
            projects_data.append(project_data)
        
        # Sort tasks by updated_at DESC before building task data
        # This ensures recently updated tasks are prioritized
        all_tasks_sorted = sorted(
            all_tasks,
            key=lambda t: (
                t.updated_at or datetime.min,
                t.created_at or datetime.min,
                t.id or 0
            ),
            reverse=True
        )
        
        # Build detailed task data with role-based filtering
        tasks_data = []
        for task in all_tasks_sorted:
            # Get user's role in the task's project
            project = next((p for p in all_user_projects if p.id == task.project_id), None)
            if not project:
                continue
            
            role = 'owner' if project.owner_id == user.id else project.get_user_role(user.id)
            
            # Re-query the task to ensure we have the absolute latest data from the database
            # This is important because tracking fields might have been updated in a different request
            try:
                fresh_task = Task.query.get(task.id)
                if fresh_task:
                    task = fresh_task
            except Exception as e:
                # If re-query fails, use the existing task object
                print(f"Warning: Could not re-query task {task.id}: {e}")
            
            # Base task data (all roles can see)
            # Include raw timestamps for sorting purposes
            task_data = {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'project_id': task.project_id,
                'status': task.status,
                'workflow_status': task.workflow_status,
                'start_date': self._format_date(task.start_date),
                'end_date': self._format_date(task.end_date),
                'created_at': self._format_timestamp(task.created_at.isoformat() if task.created_at else None),
                'updated_at': self._format_timestamp(task.updated_at.isoformat() if task.updated_at else None),
                'updated_at_raw': task.updated_at.isoformat() if task.updated_at else None,  # Raw ISO for sorting
                'created_at_raw': task.created_at.isoformat() if task.created_at else None,  # Raw ISO for sorting
                'parent_id': task.parent_id,
                'is_flagged': task.is_flagged,
                # Add tracking fields for last viewed/edited - get fresh from database
                'last_read_date': self._format_timestamp(task.task_last_read_date.isoformat() if task.task_last_read_date else None),
                'last_read_user': user_lookup.get(task.task_last_read_user, None) if task.task_last_read_user else None,
                'last_update_user': user_lookup.get(task.task_last_update_user, None) if task.task_last_update_user else None
            }
            
            # Add assignment info (all roles can see who's assigned)
            if task.assigned_to:
                task_data['assigned_to'] = {
                    'user_id': task.assigned_to,
                    'user_name': user_lookup.get(task.assigned_to, 'Unknown')
                }
            
            # Add labels (all roles can see)
            try:
                task_data['labels'] = [{'id': label.id, 'name': label.name, 'color': label.color} for label in task.labels]
            except Exception:
                task_data['labels'] = []
            
            # Add editor/admin/owner fields
            if role in ['owner', 'admin', 'editor']:
                task_data.update({
                    'priority': task.priority,
                    'size': task.size,
                    'risk_level': task.risk_level,
                    'risk_description': task.risk_description,
                    'mitigation_plan': task.mitigation_plan,
                    'started_at': self._format_timestamp(task.started_at.isoformat() if task.started_at else None),
                    'committed_at': self._format_timestamp(task.committed_at.isoformat() if task.committed_at else None),
                    'completed_at': self._format_timestamp(task.completed_at.isoformat() if task.completed_at else None)
                })
                
                # Assignment details (admin/owner can see who assigned)
                if task.assigned_by:
                    task_data['assigned_by'] = {
                        'user_id': task.assigned_by,
                        'user_name': user_lookup.get(task.assigned_by, 'Unknown')
                    }
                if task.assigned_at:
                    task_data['assigned_at'] = self._format_timestamp(task.assigned_at.isoformat())
            
            # Add flag details (all can see if flagged, admin/owner see full details)
            if task.is_flagged:
                task_data['flag_comment'] = task.flag_comment
                if task.flagged_by:
                    task_data['flagged_by'] = {
                        'user_id': task.flagged_by,
                        'user_name': user_lookup.get(task.flagged_by, 'Unknown')
                    }
                if task.flagged_at:
                    task_data['flagged_at'] = self._format_timestamp(task.flagged_at.isoformat())
                task_data['flag_resolved'] = task.flag_resolved
                
                # Admin/owner can see resolution details
                if role in ['owner', 'admin']:
                    if task.flag_resolved_at:
                        task_data['flag_resolved_at'] = self._format_timestamp(task.flag_resolved_at.isoformat())
                    if task.flag_resolved_by:
                        task_data['flag_resolved_by'] = {
                            'user_id': task.flag_resolved_by,
                            'user_name': user_lookup.get(task.flag_resolved_by, 'Unknown')
                        }
            
            # Add dependency info (all roles can see)
            try:
                dependencies = TaskDependency.query.filter_by(task_id=task.id).all()
                task_data['dependencies'] = [{'depends_on_id': dep.depends_on_id, 'type': dep.dependency_type} for dep in dependencies]
            except Exception:
                task_data['dependencies'] = []
            
            tasks_data.append(task_data)
        
        # Get stale tasks (not updated in 30+ days)
        # Use the 'now' variable set at the start of the function for consistency
        thirty_days_ago = now - timedelta(days=30)
        stale_tasks = [
            t for t in all_tasks 
            if t.status != 'completed' 
            and t.workflow_status != 'completed'
            and t.updated_at 
            and t.updated_at < thirty_days_ago
        ]
        
        # Get at-risk tasks (due within 7 days or overdue)
        # Use the 'now' variable set at the start of the function for consistency
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
            'at_risk': len(at_risk_tasks),
            'high_priority': len([t for t in all_tasks if t.priority == 'high']),
            'high_risk': len([t for t in all_tasks if t.risk_level == 'high' or t.risk_level == 'critical'])
        }
        
        return {
            'user_name': user.name,
            'user_id': user.id,
            'projects': projects_data,
            'tasks': tasks_data,  # Full task details with role-based filtering
            'task_stats': task_stats,
            'stale_tasks': [{'title': t.title, 'project_id': t.project_id} for t in stale_tasks[:10]],
            'at_risk_tasks': at_risk_tasks[:10],
            'current_time': now.isoformat(),
            'current_project_id': project_id
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
    
    def generate_response(self, user_message: str, context: Dict, project_id: Optional[int] = None, conversation_history: Optional[List[Dict]] = None) -> str:
        """Generate intelligent response using OpenAI
        
        Args:
            user_message: The user's message
            context: The user context dictionary
            project_id: Optional project ID to emphasize project-specific responses
        """
        
        if not self.client:
            return self._generate_fallback_response(user_message, context)
        
        # Filter context to current project if project_id is provided
        all_tasks = context.get('tasks', [])
        all_task_stats = context.get('task_stats', {})
        all_stale_tasks = context.get('stale_tasks', [])
        all_at_risk_tasks = context.get('at_risk_tasks', [])
        
        # Ensure project_id is an integer for comparison
        if project_id is not None:
            try:
                project_id = int(project_id)
            except (ValueError, TypeError):
                project_id = None
        
        # Get current project name if project_id is provided
        current_project_name = None
        if project_id is not None:
            # Filter all data to only include tasks from the current project
            # Use int() conversion to ensure type matching
            all_tasks = [t for t in all_tasks if t.get('project_id') is not None and int(t.get('project_id')) == project_id]
            all_stale_tasks = [t for t in all_stale_tasks if t.get('project_id') is not None and int(t.get('project_id')) == project_id]
            all_at_risk_tasks = [t for t in all_at_risk_tasks if t.get('project_id') is not None and int(t.get('project_id')) == project_id]
            
            # Recalculate task stats for current project only
            all_task_stats = {
                'total': len(all_tasks),
                'completed': len([t for t in all_tasks if t.get('status') == 'completed']),
                'in_progress': len([t for t in all_tasks if t.get('workflow_status') == 'in_progress']),
                'backlog': len([t for t in all_tasks if t.get('workflow_status') == 'backlog']),
                'committed': len([t for t in all_tasks if t.get('workflow_status') == 'committed']),
                'assigned_to_me': len([t for t in all_tasks if t.get('assigned_to', {}).get('user_id') == context.get('user_id')]),
                'flagged': len([t for t in all_tasks if t.get('is_flagged')]),
                'stale': len(all_stale_tasks),
                'at_risk': len(all_at_risk_tasks),
                'high_priority': len([t for t in all_tasks if t.get('priority') == 'high']),
                'high_risk': len([t for t in all_tasks if t.get('risk_level') in ['high', 'critical']])
            }
            
            # Get project name from context
            if context.get('projects'):
                current_project = next((p for p in context['projects'] if p.get('id') == project_id), None)
                if current_project:
                    current_project_name = current_project.get('name')
        
        # Build system prompt with context
        # Tasks are already sorted by updated_at DESC from build_user_context
        # Use raw timestamps for accurate sorting if available
        all_tasks_sorted = sorted(
            all_tasks,
            key=lambda t: (
                t.get('updated_at_raw') or t.get('updated_at') or '',
                t.get('created_at_raw') or t.get('created_at') or '',
                t.get('id', 0)
            ),
            reverse=True
        )
        
        # Create compact representation of ALL tasks (minimal fields to save tokens)
        # Format: [id, title, parent_id, updated_at, status, workflow_status, last_update_user]
        compact_tasks = []
        for task in all_tasks_sorted:
            compact_task = [
                task.get('id'),
                task.get('title', ''),
                task.get('parent_id'),
                task.get('updated_at', ''),
                task.get('status', ''),
                task.get('workflow_status', ''),
                task.get('last_update_user', '')
            ]
            # Add assigned_to if present (compact format)
            if task.get('assigned_to'):
                assigned = task.get('assigned_to', {})
                compact_task.append(assigned.get('user_name', 'Unknown'))
            else:
                compact_task.append(None)
            # Add is_flagged if true
            if task.get('is_flagged'):
                compact_task.append(True)
            compact_tasks.append(compact_task)
        
        # Get detailed info for top 20 recently updated tasks (for context)
        detailed_tasks = all_tasks_sorted[:20]
        
        # Build hierarchy map for efficient parent-child lookups
        # Format: {parent_id: [child_id1, child_id2, ...]}
        hierarchy_map = {}
        child_task_count = 0
        for task in all_tasks_sorted:
            parent_id = task.get('parent_id')
            if parent_id:
                child_task_count += 1
                if parent_id not in hierarchy_map:
                    hierarchy_map[parent_id] = []
                hierarchy_map[parent_id].append(task.get('id'))
        
        # Log task counts for verification
        print(f"AI Context: Total tasks={len(all_tasks_sorted)}, Child tasks={child_task_count}, Parent tasks={len(all_tasks_sorted) - child_task_count}")
        
        tasks_summary = {
            'total_tasks': len(all_tasks),
            'compact_tasks': compact_tasks,  # ALL tasks in compact format
            'detailed_tasks': detailed_tasks,  # Top 20 with full details
            'hierarchy': hierarchy_map  # Parent-child relationships
        }
        
        # Prepare project name text for use in prompts
        project_name_text = ""
        if project_id is not None:
            project_name_text = f'"{current_project_name}"' if current_project_name else f"Project ID {project_id}"
        
        project_context_note = ""
        if project_id is not None:
            project_context_note = f"""

CRITICAL - PROJECT CONTEXT (MANDATORY):
You are currently in the project: {project_name_text} (ID: {project_id})
- ALL tasks, statistics, and data shown below are ONLY from THIS project
- When the user asks questions, you MUST ONLY provide information about tasks and data from THIS project
- You MUST NOT mention, reference, or show tasks or information from ANY other projects
- All questions should be answered EXCLUSIVELY in the context of this specific project
- If asked about "all tasks", "when were tasks viewed/edited", or similar questions, ONLY reference tasks from this project
- The task list, statistics, stale tasks, and at-risk tasks shown below are already filtered to this project only
- When showing timestamps, use human-friendly formats like "2 hours ago", "3 days ago", "2 weeks ago" instead of ISO format
"""
        
        # Use compact JSON (no indentation) to save tokens
        compact_tasks_json = json.dumps(tasks_summary['compact_tasks'], separators=(',', ':'))
        detailed_tasks_json = json.dumps(tasks_summary['detailed_tasks'], separators=(',', ':'))
        hierarchy_json = json.dumps(tasks_summary['hierarchy'], separators=(',', ':'))
        
        system_prompt = f"""You are an AI assistant for Rhythmic, a powerful project management application.
{project_context_note}

APPLICATION KNOWLEDGE:
{self.app_knowledge}

USER CONTEXT:
Username: {context['user_name']}
User ID: {context.get('user_id', 'N/A')}

PROJECTS ({len(context['projects'])} total):
{json.dumps(context['projects'], separators=(',', ':'))}

TASK STATISTICS:
{json.dumps(all_task_stats, separators=(',', ':'))}

ALL TASKS ({tasks_summary['total_tasks']} total):
You have access to ALL {tasks_summary['total_tasks']} tasks from the current project. Tasks are sorted by most recently updated first.

COMPACT TASK LIST (ALL {tasks_summary['total_tasks']} tasks):
Format: [id, title, parent_id, updated_at, status, workflow_status, last_update_user, assigned_to_user, is_flagged]
Each array represents one task. Use this to see ALL tasks including child tasks.
{compact_tasks_json}

TASK HIERARCHY (Parent-Child Relationships):
This map shows which tasks are children of which parents: {{parent_id: [child_id1, child_id2, ...]}}
Use this to understand task relationships and find child tasks.
{hierarchy_json}

DETAILED TASK INFO (Top 20 Most Recently Updated):
These are the 20 most recently updated tasks with full details (descriptions, dates, assignments, etc.):
{detailed_tasks_json}

TASK QUERY INSTRUCTIONS:
- To find the "last updated" or "newest" task: Check the FIRST task in the compact list (tasks are sorted by updated_at DESC)
- To find child tasks: Use the hierarchy map - look up the parent_id to see all child task IDs
- To find a specific task: Search the compact list by title or ID
- Child tasks ARE included in the compact list - they have a non-null parent_id
- When asked about "all tasks", include both parent and child tasks from the compact list
- The detailed list shows full info for the 20 most recently updated tasks only

IMPORTANT NOTES:
- You can see ALL {tasks_summary['total_tasks']} tasks in the compact list above (including ALL child tasks)
- The compact list format: [id, title, parent_id, updated_at, status, workflow_status, last_update_user, assigned_to_user, is_flagged]
- Child tasks are included in the compact list - they have a non-null parent_id value
- Use the hierarchy map to find all children of a parent task: hierarchy[parent_id] returns [child_id1, child_id2, ...]
- The detailed list shows full information for the 20 most recently updated tasks
- When asked about "last updated" or "newest" tasks, the FIRST task in the compact list is the most recently updated
- All tasks shown are from the current project {project_name_text if project_id is not None else 'only'}
{f' IMPORTANT: All {tasks_summary["total_tasks"]} tasks shown are from the current project {project_name_text} only. Do NOT reference tasks from other projects.' if project_id is not None and project_name_text else ''}

STALE TASKS ({len(all_stale_tasks)}): Tasks not updated in 30+ days
{json.dumps(all_stale_tasks[:5], separators=(',', ':'))}

AT-RISK TASKS ({len(all_at_risk_tasks)}): Due within 7 days or overdue
{json.dumps(all_at_risk_tasks[:5], separators=(',', ':'))}

ROLE-BASED PERMISSIONS:
- Viewer: Can see basic task info, assignments, labels, dependencies
- Editor: Can see all viewer info + priority, size, risk details, workflow timestamps
- Admin/Owner: Can see all editor info + assignment history, flag resolution details, project management fields

RESPONSE GUIDELINES:
1. Be conversational, helpful, and concise
2. Provide specific, actionable advice based on user's actual data
3. Use formatting: Use HTML for rich responses (<h4>, <ul>, <li>, <p>, <strong>)
4. For lists, use <ul class="list-disc list-inside space-y-1 text-sm"> and <li> tags
5. For headings, use <h4 class="text-blue-400 mb-2">
6. For warnings, use <h4 class="text-orange-400 mb-2">
7. For success, use <h4 class="text-green-400 mb-2">
8. Only suggest actions the user has permission to perform based on their role
9. Reference specific tasks by title from the current project only
10. You can answer detailed questions about any task, assignment, risk, or flag from the current project
11. When mentioning tasks, be specific with names/IDs from the current project only
12. When a project context is provided (project_id is set), you MUST ONLY answer questions about that specific project
13. For date/time related questions:
    - Use the current_time from the context as the reference point for ALL time calculations - use this EXACT timestamp for all calculations
    - Calculate time differences by parsing both timestamps as ISO format and subtracting them
    - Always format the result as human-friendly relative time (e.g., "2 hours ago", "just now", "3 days ago")

RESPONSE FORMAT:
- Use HTML for formatting
- Keep responses concise but informative
- Include actionable suggestions when relevant
- Reference specific task IDs, project names, and user names when helpful"""

        # Build messages array with conversation history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500  # Increased to handle more detailed responses with full context
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

