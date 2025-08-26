# Application Architecture

## Overview

This LINE Bot application has been refactored to follow clean architecture principles, emphasizing:
- **Separation of Concerns**: Business logic is separated from infrastructure and presentation layers
- **Dependency Injection**: Loose coupling through dependency injection container
- **Single Responsibility**: Each module has a single, well-defined purpose
- **Testability**: All components are easily testable in isolation

## Directory Structure

```
/workspace/
├── core/                    # Core utilities and shared components
│   ├── constants.py        # Application constants
│   ├── container.py        # Dependency injection container
│   ├── exceptions.py       # Custom exception classes
│   └── logging_config.py   # Logging configuration
│
├── services/               # Business logic layer
│   ├── audio_service.py   # Audio processing service
│   ├── auth_service.py    # Authentication service
│   └── message_service.py # Message handling service
│
├── repositories/           # Data access layer
│   └── user_repository.py # User data repository
│
├── handlers_refactored.py # Event handlers (controller layer)
├── app_refactored.py      # Main application entry point
│
├── utils/                  # Legacy utilities (to be refactored)
├── manager/               # Question and rich menu managers
├── category/              # Question data files
└── templates/             # HTML templates
```

## Architecture Layers

### 1. Core Layer (`/core`)
Foundation utilities used across the application:
- **Constants**: Centralized configuration values
- **Exceptions**: Custom exception hierarchy for better error handling
- **Logging**: Consistent logging configuration
- **Container**: Dependency injection container for managing services

### 2. Repository Layer (`/repositories`)
Data access abstraction:
- **UserRepository**: Handles all user data persistence operations
- Provides async methods for CRUD operations
- Manages data file I/O with proper locking
- Abstracts storage implementation from business logic

### 3. Service Layer (`/services`)
Business logic implementation:
- **AudioService**: Audio transcription and processing
- **AuthService**: User authentication and registration
- **MessageService**: LINE message sending operations
- Each service is focused on a specific business domain

### 4. Handler Layer (`/handlers_refactored.py`)
Request handling and orchestration:
- **MessageHandler**: Orchestrates services to handle LINE events
- Handles error recovery and logging
- Transforms service responses to appropriate LINE messages

### 5. Application Layer (`/app_refactored.py`)
FastAPI application setup:
- Route definitions
- Lifespan management
- Dependency injection configuration
- Auto-save background tasks

## Key Design Patterns

### Dependency Injection
```python
# Services are registered in the container
container.register_singleton('audio_service', AudioService(client, line_bot_api_blob))

# And retrieved when needed
audio_service = container.get('audio_service')
```

### Repository Pattern
```python
# Data access is abstracted through repositories
user = await user_repository.get_user(user_id)
await user_repository.update_user(user_id, updates)
```

### Service Layer Pattern
```python
# Business logic is encapsulated in services
transcript = await audio_service.transcribe_audio(audio_content)
is_logged_in = await auth_service.check_user_login(user_id)
```

## Benefits of This Architecture

1. **Maintainability**: Clear separation of concerns makes code easier to understand and modify
2. **Testability**: Each component can be tested in isolation with mock dependencies
3. **Scalability**: New features can be added without affecting existing code
4. **Reusability**: Services can be reused across different handlers and endpoints
5. **Error Handling**: Centralized error handling with custom exceptions
6. **Logging**: Consistent logging across all components

## Migration Guide

### From Old to New Architecture

#### Old Code:
```python
# handlers.py - Mixed concerns
async def handle_text_message(event):
    message = event.message.text.strip()
    user_id = event.source.user_id
    
    # Direct data access
    if hasData(user_id):
        # Business logic mixed with handler
        # ...
```

#### New Code:
```python
# handlers_refactored.py - Separated concerns
class MessageHandler:
    async def handle_text_message(self, event):
        # Use services for business logic
        if not await self.auth_service.check_user_login(user_id, message):
            await self._send_registration_prompt(event, user_id)
```

## Future Improvements

1. **Database Integration**: Replace JSON file storage with a proper database
2. **Caching Layer**: Add Redis for caching frequently accessed data
3. **Message Queue**: Implement message queue for async processing
4. **API Gateway**: Add API gateway for rate limiting and authentication
5. **Monitoring**: Integrate APM tools for performance monitoring
6. **Testing**: Add comprehensive unit and integration tests

## Configuration

### Environment Variables
- `LINE_CHANNEL_ACCESS_TOKEN`: LINE channel access token
- `LINE_CHANNEL_SECRET`: LINE channel secret
- `OPENAI_API_KEY`: OpenAI API key
- `DOMAIN`: Application domain

### Constants Configuration
Edit `/core/constants.py` to modify:
- Chat categories
- File paths
- Timeout values
- Auto-save intervals

## Development Guidelines

1. **Adding New Features**:
   - Create service in `/services` for business logic
   - Add repository methods if data access is needed
   - Update handler to orchestrate services
   - Register new services in container

2. **Error Handling**:
   - Use custom exceptions from `/core/exceptions.py`
   - Log errors appropriately
   - Provide user-friendly error messages

3. **Logging**:
   - Use `get_logger(__name__)` in each module
   - Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)
   - Include context in log messages

4. **Testing**:
   - Write unit tests for services
   - Mock external dependencies
   - Test error scenarios

## Running the Application

### Development
```bash
python app_refactored.py
```

### Production
```bash
uvicorn app_refactored:app --host 0.0.0.0 --port 8000
```

### Docker
```bash
docker-compose up
```