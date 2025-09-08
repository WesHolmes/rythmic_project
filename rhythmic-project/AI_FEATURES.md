# AI Assistant Features

Rhythmic now includes AI-powered features to help you create comprehensive project briefs and generate starter project plans.

## Features

### 1. AI Project Brief Generation
- **What it does**: Generates a comprehensive project brief from your project description
- **How to use**: 
  1. Go to "New Project"
  2. Enter your project name and describe what you're trying to achieve
  3. Click "Generate Project Brief"
  4. Review the AI-generated brief and click "Use This Brief" to populate the form

### 2. AI Starter Task Generation
- **What it does**: Creates a starter set of tasks based on your project brief
- **How to use**:
  1. Create a project with a comprehensive brief (vision, problems, timeline, impact, goals)
  2. Go to the project detail page
  3. Click "Generate Starter Tasks"
  4. Review and modify the generated tasks as needed

### 3. AI Project Summary
- **What it does**: Generates intelligent project summaries based on current status
- **How to use**:
  1. Go to any project detail page
  2. Click "AI Summary"
  3. View the generated summary in a modal

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key

### 3. Configure Environment
1. Copy `env.example` to `.env`
2. Add your OpenAI API key:
```
OPENAI_API_KEY=your-actual-api-key-here
```

### 4. Run Setup Script (Optional)
```bash
python setup_ai.py
```

## API Endpoints

### Generate Project Brief
- **Endpoint**: `POST /api/generate-brief`
- **Body**: `{"project_name": "string", "user_input": "string"}`
- **Response**: `{"brief": {"vision": "...", "problems": "...", "timeline": "...", "impact": "...", "goals": "..."}}`

### Generate Starter Plan
- **Endpoint**: `POST /api/generate-starter-plan`
- **Body**: `{"project_name": "string", "project_brief": {...}}`
- **Response**: `{"tasks": [{"title": "...", "description": "...", "priority": "...", "size": "...", "estimated_duration": 5, "suggested_start_offset": 0}]}`

### Generate Project Summary
- **Endpoint**: `POST /api/generate-summary`
- **Body**: `{"project_id": 123}`
- **Response**: `{"summary": "Generated project summary text..."}`

### Generate Starter Tasks
- **Endpoint**: `POST /projects/<id>/generate-tasks`
- **Body**: None (uses project brief from database)
- **Response**: `{"message": "Successfully created X starter tasks", "tasks_created": X}`

## AI Service Architecture

The AI functionality is implemented in `ai_service.py` with the following components:

### AIAssistant Class
- **generate_project_brief()**: Creates structured project briefs
- **generate_starter_project_plan()**: Generates task lists with metadata
- **generate_project_summary()**: Creates intelligent project summaries

### Error Handling
- Graceful fallbacks when AI service is unavailable
- Fallback briefs and tasks for offline functionality
- Comprehensive error logging

### Security
- API keys stored in environment variables
- No sensitive data sent to AI service
- Input validation and sanitization

## Best Practices

### For Project Briefs
- Be specific about your project goals
- Include timeline constraints
- Mention key stakeholders or requirements
- Describe the problems you're solving

### For Task Generation
- Ensure your project brief is comprehensive
- Review generated tasks before using them
- Modify task priorities and sizes as needed
- Add additional tasks that AI might have missed

### For Summaries
- Use summaries for stakeholder updates
- Generate summaries after significant progress
- Customize summaries for different audiences

## Troubleshooting

### Common Issues

1. **"AI service not available"**
   - Check your OpenAI API key
   - Verify internet connection
   - Check API quota/usage limits

2. **"Failed to generate brief"**
   - Ensure project name and description are provided
   - Check API key permissions
   - Try with shorter input text

3. **"No tasks generated"**
   - Verify project brief is complete
   - Check that vision, problems, and goals are filled
   - Try regenerating with more detailed brief

### Debug Mode
Set `FLASK_DEBUG=True` in your `.env` file to see detailed error messages.

## Cost Considerations

- OpenAI API usage is charged per token
- Brief generation: ~500-1000 tokens per request
- Task generation: ~800-1500 tokens per request
- Summary generation: ~300-600 tokens per request
- Monitor usage at [OpenAI Usage Dashboard](https://platform.openai.com/usage)

## Future Enhancements

- Custom AI prompts for different project types
- Integration with other AI models
- Batch processing for multiple projects
- AI-powered task prioritization
- Smart deadline suggestions
- Risk assessment and mitigation recommendations
