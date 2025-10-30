import os
import json
import time
from datetime import datetime, timedelta
from openai import OpenAI
from typing import Dict, List, Optional

class AIAssistant:
    def __init__(self):
        api_key = os.environ.get('OPENAI_API_KEY')
        model = os.environ.get('AI_MODEL', 'gpt-4o')  # Default to GPT-4o, fallback to gpt-3.5-turbo
        
        if not api_key:
            print("⚠️  OPENAI_API_KEY not found. AI features will use fallback responses.")
            self.client = None
            self.model = 'fallback'
        else:
            try:
                self.client = OpenAI(api_key=api_key)
                self.model = model
            except Exception as e:
                print(f"⚠️  Failed to initialize OpenAI client: {e}. Using fallback responses.")
                self.client = None
                self.model = 'fallback'
    
    def generate_project_brief(self, project_name: str, user_input: str) -> Dict[str, str]:
        """
        Generate a comprehensive project brief from user input
        """
        prompt = f"""
        You are an expert project manager and business strategist. Based on the project name "{project_name}" and the following user input, create a comprehensive project brief.

        User Input: {user_input}

        Please provide a structured project brief with the following sections:
        1. Vision: A clear, inspiring vision statement for the project
        2. Problems: The specific problems this project aims to solve
        3. Timeline: Suggested timeline with key phases
        4. Impact: Expected business impact and outcomes
        5. Goals: Specific, measurable goals for the project

        Format your response as a JSON object with these exact keys: vision, problems, timeline, impact, goals
        Each value should be a well-written paragraph (2-4 sentences).
        """
        
        # Check if client is available
        if not self.client:
            print("OpenAI client not available, using fallback brief")
            return self._get_fallback_brief(project_name, user_input)
        
        # Try with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert project manager who creates comprehensive, actionable project briefs. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                content = response.choices[0].message.content.strip()
                # Try to parse as JSON, fallback to structured text if needed
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # If not valid JSON, create a structured response
                    return self._parse_text_to_brief(content)
                    
            except Exception as e:
                error_msg = str(e)
                print(f"AI Service Error (attempt {attempt + 1}/{max_retries}): {e}")
                
                # Check for specific error types
                if "insufficient_quota" in error_msg or "quota" in error_msg.lower():
                    print("⚠️  OpenAI API quota exceeded. Please check your billing and add credits.")
                    print("💡 Using dynamic fallback instead of retrying quota errors.")
                    return self._get_fallback_brief(project_name, user_input)
                elif "rate_limit" in error_msg.lower():
                    print("⚠️  Rate limit hit. Waiting longer before retry...")
                    if attempt < max_retries - 1:
                        time.sleep(5)  # Wait 5 seconds for rate limits
                        continue
                elif attempt < max_retries - 1:
                    time.sleep(1)  # Wait 1 second before retry for other errors
                    continue
                else:
                    print("All retry attempts failed, using dynamic fallback")
                    return self._get_fallback_brief(project_name, user_input)
    
    def generate_starter_project_plan(self, project_name: str, project_brief: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Generate a starter project plan with tasks based on the project brief
        """
        brief_text = f"""
        Project: {project_name}
        Vision: {project_brief.get('vision', '')}
        Problems: {project_brief.get('problems', '')}
        Timeline: {project_brief.get('timeline', '')}
        Impact: {project_brief.get('impact', '')}
        Goals: {project_brief.get('goals', '')}
        """
        
        prompt = f"""
        You are an expert project manager. Based on the following project brief, create a starter project plan with 5-8 high-level tasks that would be needed to execute this project.

        {brief_text}

        For each task, provide:
        - title: A clear, actionable task title
        - description: A detailed description of what needs to be done
        - priority: high, medium, or low
        - size: small, medium, or large
        - estimated_duration: Number of days (1-30)
        - suggested_start_offset: Days from project start (0-30)

        Format your response as a JSON array of objects with these exact keys: title, description, priority, size, estimated_duration, suggested_start_offset
        """
        
        # Check if client is available
        if not self.client:
            print("OpenAI client not available, using fallback tasks")
            return self._get_fallback_tasks(project_name)
        
        # Try with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert project manager who creates practical, actionable project plans. Always respond with valid JSON arrays."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1500
                )
                
                content = response.choices[0].message.content.strip()
                try:
                    tasks = json.loads(content)
                    return tasks if isinstance(tasks, list) else []
                except json.JSONDecodeError:
                    return self._parse_text_to_tasks(content)
                    
            except Exception as e:
                error_msg = str(e)
                print(f"AI Service Error (attempt {attempt + 1}/{max_retries}): {e}")
                
                # Check for specific error types
                if "insufficient_quota" in error_msg or "quota" in error_msg.lower():
                    print("⚠️  OpenAI API quota exceeded. Please check your billing and add credits.")
                    print("💡 Using dynamic fallback instead of retrying quota errors.")
                    return self._get_fallback_tasks(project_name)
                elif "rate_limit" in error_msg.lower():
                    print("⚠️  Rate limit hit. Waiting longer before retry...")
                    if attempt < max_retries - 1:
                        time.sleep(5)  # Wait 5 seconds for rate limits
                        continue
                elif attempt < max_retries - 1:
                    time.sleep(1)  # Wait 1 second before retry for other errors
                    continue
                else:
                    print("All retry attempts failed, using dynamic fallback")
                    return self._get_fallback_tasks(project_name)
    
    def generate_project_summary(self, project_name: str, tasks: List[Dict], project_brief: Dict[str, str]) -> str:
        """
        Generate an AI-driven project summary
        """
        tasks_summary = "\n".join([f"- {task.get('title', 'Unknown Task')}: {task.get('status', 'Unknown Status')}" for task in tasks])
        
        prompt = f"""
        You are an expert project manager. Create a concise, professional project summary for "{project_name}".

        Project Brief:
        Vision: {project_brief.get('vision', 'Not specified')}
        Goals: {project_brief.get('goals', 'Not specified')}

        Current Tasks:
        {tasks_summary}

        Provide a 2-3 paragraph summary that includes:
        1. Project overview and objectives
        2. Current status and key activities
        3. Next steps and priorities

        Keep it professional and actionable.
        """
        
        # Check if client is available
        if not self.client:
            print("OpenAI client not available, using fallback summary")
            return self._get_fallback_summary(project_name, tasks, project_brief)
        
        # Try with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert project manager who creates clear, actionable project summaries."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                error_msg = str(e)
                print(f"AI Service Error (attempt {attempt + 1}/{max_retries}): {e}")
                
                # Check for specific error types
                if "insufficient_quota" in error_msg or "quota" in error_msg.lower():
                    print("⚠️  OpenAI API quota exceeded. Please check your billing and add credits.")
                    print("💡 Using dynamic fallback instead of retrying quota errors.")
                    return self._get_fallback_summary(project_name, tasks, project_brief)
                elif "rate_limit" in error_msg.lower():
                    print("⚠️  Rate limit hit. Waiting longer before retry...")
                    if attempt < max_retries - 1:
                        time.sleep(5)  # Wait 5 seconds for rate limits
                        continue
                elif attempt < max_retries - 1:
                    time.sleep(1)  # Wait 1 second before retry for other errors
                    continue
                else:
                    print("All retry attempts failed, using dynamic fallback")
                    return self._get_fallback_summary(project_name, tasks, project_brief)
    
    def _parse_text_to_brief(self, text: str) -> Dict[str, str]:
        """Parse text response into structured brief"""
        lines = text.split('\n')
        brief = {}
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if line.lower().startswith(('vision:', 'problems:', 'timeline:', 'impact:', 'goals:')):
                if current_section:
                    brief[current_section] = ' '.join(current_content)
                current_section = line.split(':')[0].lower()
                current_content = [line.split(':', 1)[1].strip()] if ':' in line else []
            elif current_section and line:
                current_content.append(line)
        
        if current_section:
            brief[current_section] = ' '.join(current_content)
        
        return brief
    
    def _parse_text_to_tasks(self, text: str) -> List[Dict[str, str]]:
        """Parse text response into task list"""
        # Simple fallback parsing - in practice, you'd want more robust parsing
        tasks = []
        lines = text.split('\n')
        
        for line in lines:
            if line.strip() and not line.strip().startswith('#'):
                tasks.append({
                    'title': line.strip(),
                    'description': f'Task: {line.strip()}',
                    'priority': 'medium',
                    'size': 'medium',
                    'estimated_duration': 5,
                    'suggested_start_offset': len(tasks) * 2
                })
        
        return tasks[:8]  # Limit to 8 tasks
    
    def _get_fallback_summary(self, project_name: str, tasks: List[Dict], project_brief: Dict[str, str]) -> str:
        """Generate dynamic fallback summary when AI service fails"""
        # Count tasks by status
        task_counts = {}
        for task in tasks:
            status = task.get('status', 'unknown')
            task_counts[status] = task_counts.get(status, 0) + 1
        
        # Generate summary based on available data
        total_tasks = len(tasks)
        completed_tasks = task_counts.get('completed', 0)
        in_progress_tasks = task_counts.get('in_progress', 0)
        
        # Extract key information from project brief
        vision = project_brief.get('vision', 'Not specified')
        goals = project_brief.get('goals', 'Not specified')
        
        summary = f"""Project Summary for {project_name}

Project Overview:
{vision}

Current Status:
The project is actively progressing with {total_tasks} total tasks. Currently, {completed_tasks} tasks have been completed and {in_progress_tasks} tasks are in progress.

Key Objectives:
{goals}

Next Steps:
Continue executing the remaining tasks according to the project plan. Focus on completing in-progress items and moving pending tasks forward to maintain project momentum."""
        
        return summary
    
    def _get_fallback_brief(self, project_name: str, user_input: str) -> Dict[str, str]:
        """Generate dynamic fallback brief when AI service fails"""
        # Try to extract key information from user input
        user_input_lower = user_input.lower()
        
        # Analyze user input for project type and context
        if any(word in user_input_lower for word in ['website', 'web', 'app', 'application']):
            project_type = "digital product"
            timeline_hint = "typically 2-6 months depending on complexity"
        elif any(word in user_input_lower for word in ['marketing', 'campaign', 'brand']):
            project_type = "marketing initiative"
            timeline_hint = "usually 1-3 months with ongoing optimization"
        elif any(word in user_input_lower for word in ['process', 'workflow', 'system']):
            project_type = "process improvement"
            timeline_hint = "typically 1-4 months including implementation"
        else:
            project_type = "business initiative"
            timeline_hint = "timeline to be determined based on scope"
        
        # Extract key problems/needs from user input
        problems_text = user_input[:300] if len(user_input) > 50 else f"Address the specific requirements and challenges outlined for {project_name}"
        
        # Generate more contextual responses
        return {
            'vision': f"To successfully deliver {project_name} as a {project_type} that meets stakeholder expectations and drives meaningful business value.",
            'problems': f"Key challenges to address: {problems_text}",
            'timeline': f"Project timeline: {timeline_hint}. Specific phases and milestones to be defined during planning.",
            'impact': f"Expected impact: Improved efficiency, stakeholder satisfaction, and successful delivery of {project_name} objectives.",
            'goals': f"Primary goals: Complete {project_name} on time, within scope, and achieve the desired outcomes outlined in the project requirements."
        }
    
    def _get_fallback_tasks(self, project_name: str) -> List[Dict[str, str]]:
        """Generate dynamic fallback tasks when AI service fails"""
        # Analyze project name for context
        project_lower = project_name.lower()
        
        # Determine project type and adjust tasks accordingly
        if any(word in project_lower for word in ['website', 'web', 'app', 'application']):
            tasks = [
                {
                    'title': f'Project Planning for {project_name}',
                    'description': 'Define project scope, technical requirements, and development timeline',
                    'priority': 'high',
                    'size': 'medium',
                    'estimated_duration': 3,
                    'suggested_start_offset': 0
                },
                {
                    'title': 'Technical Architecture Design',
                    'description': 'Design system architecture, database schema, and technical specifications',
                    'priority': 'high',
                    'size': 'medium',
                    'estimated_duration': 5,
                    'suggested_start_offset': 3
                },
                {
                    'title': 'Development and Implementation',
                    'description': 'Build core functionality and features according to specifications',
                    'priority': 'high',
                    'size': 'large',
                    'estimated_duration': 15,
                    'suggested_start_offset': 8
                },
                {
                    'title': 'Testing and Quality Assurance',
                    'description': 'Perform comprehensive testing including unit, integration, and user acceptance testing',
                    'priority': 'high',
                    'size': 'medium',
                    'estimated_duration': 5,
                    'suggested_start_offset': 23
                },
                {
                    'title': 'Deployment and Launch',
                    'description': 'Deploy to production environment and conduct final launch activities',
                    'priority': 'high',
                    'size': 'small',
                    'estimated_duration': 3,
                    'suggested_start_offset': 28
                }
            ]
        elif any(word in project_lower for word in ['marketing', 'campaign', 'brand']):
            tasks = [
                {
                    'title': f'Strategy Development for {project_name}',
                    'description': 'Develop marketing strategy, target audience analysis, and campaign objectives',
                    'priority': 'high',
                    'size': 'medium',
                    'estimated_duration': 4,
                    'suggested_start_offset': 0
                },
                {
                    'title': 'Creative Development',
                    'description': 'Create marketing materials, content, and creative assets',
                    'priority': 'high',
                    'size': 'medium',
                    'estimated_duration': 6,
                    'suggested_start_offset': 4
                },
                {
                    'title': 'Campaign Implementation',
                    'description': 'Execute marketing campaigns across selected channels and platforms',
                    'priority': 'high',
                    'size': 'large',
                    'estimated_duration': 8,
                    'suggested_start_offset': 10
                },
                {
                    'title': 'Performance Monitoring',
                    'description': 'Track campaign performance, analyze metrics, and optimize results',
                    'priority': 'medium',
                    'size': 'medium',
                    'estimated_duration': 4,
                    'suggested_start_offset': 18
                },
                {
                    'title': 'Campaign Analysis and Reporting',
                    'description': 'Compile results, insights, and recommendations for future campaigns',
                    'priority': 'medium',
                    'size': 'small',
                    'estimated_duration': 2,
                    'suggested_start_offset': 22
                }
            ]
        else:
            # Generic project tasks
            tasks = [
                {
                    'title': f'Project Planning for {project_name}',
                    'description': 'Define project scope, timeline, resources, and success criteria',
                    'priority': 'high',
                    'size': 'medium',
                    'estimated_duration': 3,
                    'suggested_start_offset': 0
                },
                {
                    'title': 'Requirements Analysis',
                    'description': 'Gather and document detailed project requirements and specifications',
                    'priority': 'high',
                    'size': 'medium',
                    'estimated_duration': 5,
                    'suggested_start_offset': 3
                },
                {
                    'title': 'Project Execution',
                    'description': 'Implement core project deliverables and manage day-to-day activities',
                    'priority': 'high',
                    'size': 'large',
                    'estimated_duration': 12,
                    'suggested_start_offset': 8
                },
                {
                    'title': 'Quality Control and Testing',
                    'description': 'Review deliverables, conduct quality checks, and validate outcomes',
                    'priority': 'medium',
                    'size': 'medium',
                    'estimated_duration': 4,
                    'suggested_start_offset': 20
                },
                {
                    'title': 'Project Closure and Handover',
                    'description': 'Finalize deliverables, conduct project review, and transfer ownership',
                    'priority': 'high',
                    'size': 'small',
                    'estimated_duration': 2,
                    'suggested_start_offset': 24
                }
            ]
        
        return tasks