# English Learning Bot - Improved Architecture

This project is a LINE Bot application for English learning and speech assessment, now featuring a clean, decoupled architecture for better maintainability and reusability.

## 🏗️ Architecture Overview

The codebase has been refactored to follow clean architecture principles with clear separation of concerns:

### 📁 Project Structure

```
├── app.py                 # FastAPI application entry point
├── config.py             # Configuration management
├── constants.py          # Centralized constants and configuration values
├── routes.py             # HTTP route handlers
├── analyze.py            # Data analysis functionality
├── requirements.txt      # Python dependencies
├── handlers/             # Event handlers (decoupled from business logic)
│   ├── __init__.py
│   ├── base_handler.py   # Abstract base handler
│   ├── audio_handler.py  # Audio message handler
│   ├── text_handler.py   # Text message handler
│   └── postback_handler.py # Postback event handler
├── services/             # Business logic layer
│   ├── __init__.py
│   ├── container.py      # Dependency injection container
│   ├── audio_service.py  # Audio processing service
│   ├── assessment_service.py # Speech assessment service
│   └── user_service.py   # User management service
├── interfaces/           # Abstract interfaces for better testability
│   ├── __init__.py
│   ├── handlers.py       # Handler interfaces
│   └── services.py       # Service interfaces
├── utils/                # Utility modules
│   ├── __init__.py
│   ├── models.py         # Pydantic data models
│   ├── file_utils.py     # File handling utilities
│   ├── message_utils.py  # LINE Bot messaging utilities
│   └── error_handler.py  # Centralized error handling
├── manager/              # Question and rich menu management
└── templates/            # Static files and templates
```

## 🎯 Key Improvements

### 1. **Service Layer Architecture**
- **Separation of Concerns**: Business logic moved to dedicated service classes
- **Dependency Injection**: Services are managed through a container pattern
- **Interface-Based Design**: All services implement abstract interfaces for better testability

### 2. **Improved Error Handling**
- **Centralized Error Management**: Consistent error handling across the application
- **Custom Exception Classes**: Typed exceptions for different error scenarios
- **Logging**: Comprehensive logging for debugging and monitoring

### 3. **Configuration Management**
- **Environment Validation**: Automatic validation of required environment variables
- **Centralized Constants**: All magic numbers and strings moved to constants module
- **Type Safety**: Full type hints throughout the codebase

### 4. **Handler Refactoring**
- **Single Responsibility**: Each handler focuses on one type of event
- **Reusable Base Class**: Common functionality abstracted to base handler
- **Clean Interfaces**: Handlers implement clear interfaces

## 🚀 Services

### AudioService
Handles all audio processing operations:
- Audio content retrieval from LINE Bot API
- Audio format conversion (M4A to MP3)
- Speech transcription using OpenAI Whisper

### AssessmentService  
Manages speech assessment:
- AI-powered speech evaluation using GPT models
- Assessment validation and scoring
- Configurable assessment criteria

### UserService
Manages user operations:
- User registration and validation
- User state management
- Assessment history tracking

## 🔧 Usage

### Environment Setup
```bash
# Required environment variables
LINE_CHANNEL_ACCESS_TOKEN=your_line_token
LINE_CHANNEL_SECRET=your_line_secret
DOMAIN=your_domain
OPENAI_API_KEY=your_openai_key
```

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Start the application
python app.py
```

### Adding New Features

#### 1. Adding a New Service
```python
# 1. Define interface in interfaces/services.py
class INewService(ABC):
    @abstractmethod
    async def new_method(self) -> bool:
        pass

# 2. Implement service in services/
class NewService(INewService):
    async def new_method(self) -> bool:
        # Implementation
        return True

# 3. Register in container (app.py)
container.set_new_service(NewService())
```

#### 2. Adding a New Handler
```python
# 1. Create handler in handlers/
class NewHandler(BaseHandler, INewHandler):
    async def handle(self, event) -> bool:
        # Implementation
        return True

# 2. Register in handlers/__init__.py
new_handler = NewHandler()
```

## 🧪 Testing

The interface-based design makes testing much easier:

```python
# Mock services for testing
class MockAudioService(IAudioService):
    async def transcribe_audio(self, content: bytes, language: str) -> str:
        return "test transcription"

# Inject mock for testing
container.set_audio_service(MockAudioService())
```

## 📊 Benefits of the New Architecture

1. **Maintainability**: Clear separation makes code easier to understand and modify
2. **Testability**: Interface-based design enables easy mocking and unit testing
3. **Reusability**: Services can be reused across different handlers and contexts
4. **Scalability**: New features can be added without affecting existing code
5. **Error Handling**: Consistent error management reduces bugs and improves reliability
6. **Type Safety**: Comprehensive type hints catch errors at development time

## 🔄 Migration Notes

The refactoring maintains backward compatibility while providing the new architecture benefits:

- All existing functionality is preserved
- API endpoints remain the same
- Database schema unchanged
- Environment variables unchanged

## 🤝 Contributing

When contributing to this project:

1. Follow the established service layer pattern
2. Implement appropriate interfaces for new services
3. Add comprehensive type hints
4. Use the centralized error handling patterns
5. Update constants.py for any new configuration values
6. Write tests for new functionality

## 📝 License

This project maintains its original licensing terms while providing improved architecture and maintainability.