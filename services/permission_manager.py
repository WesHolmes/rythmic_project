"""
Permission Manager Service

Handles permission checking for project access and operations.
Replaces the deleted permission_manager module with essential functionality.
"""

from typing import Optional
from flask_login import current_user


class PermissionManager:
    """Simple permission manager for project access control"""
    
    @staticmethod
    def can_access_project(user_id: int, project_id: int) -> bool:
        """Check if user can access a project"""
        from app import Project
        
        project = Project.query.get(project_id)
        if not project:
            return False
        
        # Owner can always access
        if project.owner_id == user_id:
            return True
        
        # Check if user is a collaborator
        return project.has_collaborator(user_id)
    
    @staticmethod
    def can_edit_project(project, user_id: Optional[int] = None) -> bool:
        """Check if user can edit a project"""
        if user_id is None:
            if not current_user.is_authenticated:
                return False
            user_id = current_user.id
        
        # Owner can always edit
        if project.owner_id == user_id:
            return True
        
        # Check if user is admin or editor collaborator
        user_role = project.get_user_role(user_id)
        return user_role in ['admin', 'editor']
    
    @staticmethod
    def can_delete_project(project, user_id: Optional[int] = None) -> bool:
        """Check if user can delete a project"""
        if user_id is None:
            if not current_user.is_authenticated:
                return False
            user_id = current_user.id
        
        # Only owner can delete
        return project.owner_id == user_id
    
    @staticmethod
    def can_manage_collaborators(project, user_id: Optional[int] = None) -> bool:
        """Check if user can manage project collaborators"""
        if user_id is None:
            if not current_user.is_authenticated:
                return False
            user_id = current_user.id
        
        # Owner can always manage
        if project.owner_id == user_id:
            return True
        
        # Check if user is admin collaborator
        user_role = project.get_user_role(user_id)
        return user_role == 'admin'
    
    @staticmethod
    def can_share_project(project, user_id: Optional[int] = None) -> bool:
        """Check if user can share a project"""
        if user_id is None:
            if not current_user.is_authenticated:
                return False
            user_id = current_user.id
        
        # Owner can always share
        if project.owner_id == user_id:
            return True
        
        # Check if user is admin collaborator
        user_role = project.get_user_role(user_id)
        return user_role == 'admin'
    
    @staticmethod
    def can_create_tasks(project, user_id: Optional[int] = None) -> bool:
        """Check if user can create tasks in a project"""
        if user_id is None:
            if not current_user.is_authenticated:
                return False
            user_id = current_user.id
        
        # Owner can always create tasks
        if project.owner_id == user_id:
            return True
        
        # Check if user is admin or editor collaborator
        user_role = project.get_user_role(user_id)
        return user_role in ['admin', 'editor']
    
    @staticmethod
    def can_edit_tasks(project, user_id: Optional[int] = None) -> bool:
        """Check if user can edit tasks in a project"""
        return PermissionManager.can_create_tasks(project, user_id)
    
    @staticmethod
    def can_delete_tasks(project, user_id: Optional[int] = None) -> bool:
        """Check if user can delete tasks in a project"""
        return PermissionManager.can_edit_project(project, user_id)
    
    @staticmethod
    def can_manage_labels(project, user_id: Optional[int] = None) -> bool:
        """Check if user can manage labels in a project"""
        return PermissionManager.can_edit_project(project, user_id)
    
    @staticmethod
    def get_user_role(user_id: int, project_id: int) -> Optional[str]:
        """Get user's role in a project"""
        from app import Project
        
        project = Project.query.get(project_id)
        if not project:
            return None
        
        return project.get_user_role(user_id)
    
    @staticmethod
    def require_access(project, user_id: Optional[int] = None) -> bool:
        """Require access to project, raise exception if denied"""
        if not PermissionManager.can_access_project(project, user_id):
            from flask import abort
            abort(403)
        return True
    
    @staticmethod
    def require_edit_permission(project, user_id: Optional[int] = None) -> bool:
        """Require edit permission, raise exception if denied"""
        if not PermissionManager.can_edit_project(project, user_id):
            from flask import abort
            abort(403)
        return True
    
    @staticmethod
    def require_admin_permission(project, user_id: Optional[int] = None) -> bool:
        """Require admin permission, raise exception if denied"""
        if not PermissionManager.can_manage_collaborators(project, user_id):
            from flask import abort
            abort(403)
        return True
    
    @staticmethod
    def get_accessible_projects(user_id: int) -> list:
        """Get list of project IDs that user can access (owned + shared)"""
        from app import Project, ProjectCollaborator
        
        # Get owned projects
        owned_projects = Project.query.filter_by(owner_id=user_id).all()
        owned_project_ids = [p.id for p in owned_projects]
        
        # Get shared projects (where user is an accepted collaborator)
        shared_collaborations = ProjectCollaborator.query.filter_by(
            user_id=user_id,
            status=ProjectCollaborator.STATUS_ACCEPTED
        ).all()
        shared_project_ids = [c.project_id for c in shared_collaborations]
        
        # Combine and return unique project IDs
        all_project_ids = list(set(owned_project_ids + shared_project_ids))
        return all_project_ids
    
    @staticmethod
    def has_permission(user_id: int, project_id: int, permission: str) -> bool:
        """Check if user has specific permission for a project"""
        from app import Project
        
        project = Project.query.get(project_id)
        if not project:
            return False
        
        # Map permission strings to methods
        permission_map = {
            'edit_project': PermissionManager.can_edit_project,
            'delete_project': PermissionManager.can_delete_project,
            'manage_collaborators': PermissionManager.can_manage_collaborators,
            'create_tasks': PermissionManager.can_create_tasks,
            'edit_tasks': PermissionManager.can_edit_tasks,
            'delete_tasks': PermissionManager.can_delete_tasks,
            'manage_labels': PermissionManager.can_manage_labels,
            'share_project': PermissionManager.can_share_project
        }
        
        permission_method = permission_map.get(permission)
        if permission_method:
            return permission_method(project, user_id)
        
        return False
    
    @staticmethod
    def can_manage_role(user_id: int, project_id: int, target_role: str) -> bool:
        """Check if user can manage (assign/change) a specific role"""
        from app import Project
        
        project = Project.query.get(project_id)
        if not project:
            return False
        
        # Owner can manage any role
        if project.owner_id == user_id:
            return True
        
        # Get user's current role
        user_role = project.get_user_role(user_id)
        if not user_role:
            return False
        
        # Admin can manage viewer and editor roles
        if user_role == 'admin':
            return target_role in ['viewer', 'editor']
        
        return False