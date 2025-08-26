"""Dependency injection container for managing application dependencies."""

from typing import Dict, Any, Optional
from core.logging_config import get_logger


class DIContainer:
    """Simple dependency injection container."""
    
    def __init__(self):
        """Initialize the DI container."""
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
        self._singletons: Dict[str, Any] = {}
        self.logger = get_logger(__name__)
    
    def register_singleton(self, name: str, instance: Any) -> None:
        """
        Register a singleton service.
        
        Args:
            name: Service name
            instance: Service instance
        """
        self._singletons[name] = instance
        self.logger.debug(f"Registered singleton: {name}")
    
    def register_factory(self, name: str, factory: callable) -> None:
        """
        Register a factory function for creating service instances.
        
        Args:
            name: Service name
            factory: Factory function that creates service instances
        """
        self._factories[name] = factory
        self.logger.debug(f"Registered factory: {name}")
    
    def register_service(self, name: str, service_class: type, **kwargs) -> None:
        """
        Register a service class.
        
        Args:
            name: Service name
            service_class: Service class
            **kwargs: Constructor arguments
        """
        self._services[name] = (service_class, kwargs)
        self.logger.debug(f"Registered service: {name}")
    
    def get(self, name: str) -> Any:
        """
        Get a service instance.
        
        Args:
            name: Service name
            
        Returns:
            Service instance
            
        Raises:
            ValueError: If service is not registered
        """
        # Check singletons first
        if name in self._singletons:
            return self._singletons[name]
        
        # Check factories
        if name in self._factories:
            instance = self._factories[name](self)
            return instance
        
        # Check services
        if name in self._services:
            service_class, kwargs = self._services[name]
            # Resolve dependencies in kwargs
            resolved_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str) and value.startswith('@'):
                    # Dependency reference
                    dep_name = value[1:]
                    resolved_kwargs[key] = self.get(dep_name)
                else:
                    resolved_kwargs[key] = value
            
            instance = service_class(**resolved_kwargs)
            return instance
        
        raise ValueError(f"Service '{name}' is not registered")
    
    def has(self, name: str) -> bool:
        """
        Check if a service is registered.
        
        Args:
            name: Service name
            
        Returns:
            True if service is registered
        """
        return (
            name in self._singletons or
            name in self._factories or
            name in self._services
        )
    
    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        self.logger.debug("Cleared all services")


# Global container instance
container = DIContainer()


def configure_container():
    """Configure the dependency injection container with all services."""
    from repositories.user_repository import UserRepository
    from services.audio_service import AudioService
    from services.auth_service import AuthService
    from config import (
        client, line_bot_api, line_bot_api_blob,
        question_manager, rich_menu_manager
    )
    from core.constants import DEFAULT_USER_DATA_FILE, DEFAULT_CONFIG_FILE
    
    # Register repositories
    user_repo = UserRepository(DEFAULT_USER_DATA_FILE, DEFAULT_CONFIG_FILE)
    container.register_singleton('user_repository', user_repo)
    
    # Register services
    container.register_singleton(
        'audio_service',
        AudioService(client, line_bot_api_blob)
    )
    
    container.register_singleton(
        'auth_service',
        AuthService(user_repo)
    )
    
    # Register external clients
    container.register_singleton('openai_client', client)
    container.register_singleton('line_bot_api', line_bot_api)
    container.register_singleton('line_bot_api_blob', line_bot_api_blob)
    container.register_singleton('question_manager', question_manager)
    container.register_singleton('rich_menu_manager', rich_menu_manager)
    
    return container