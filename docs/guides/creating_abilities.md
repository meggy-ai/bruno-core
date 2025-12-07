# Creating Custom Abilities

Learn how to create custom abilities that extend your assistant's capabilities.

## Overview

Abilities are pluggable skills that your assistant can execute. They follow a simple pattern:
1. Define metadata (name, description, parameters)
2. Implement execution logic
3. Return structured responses

## Basic Ability

### Step 1: Extend BaseAbility

```python
from bruno_core.base import BaseAbility
from bruno_core.models import (
    AbilityMetadata,
    AbilityParameter,
    AbilityRequest,
    AbilityResponse,
)

class WeatherAbility(BaseAbility):
    """Get weather information for locations."""
    
    def get_metadata(self) -> AbilityMetadata:
        return AbilityMetadata(
            name="weather",
            description="Get current weather and forecasts",
            version="1.0.0",
            parameters=[
                AbilityParameter(
                    name="location",
                    type="string",
                    description="City or location name",
                    required=True,
                ),
                AbilityParameter(
                    name="units",
                    type="string",
                    description="Temperature units",
                    required=False,
                    allowed_values=["celsius", "fahrenheit"],
                    default_value="celsius",
                ),
            ],
            examples=[
                "What's the weather in London?",
                "Get weather for New York",
                "Weather forecast for Tokyo",
            ],
        )
    
    async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
        """Execute the weather lookup."""
        location = request.parameters.get("location")
        units = request.parameters.get("units", "celsius")
        
        try:
            # Your implementation here
            weather_data = await self._fetch_weather(location, units)
            
            return AbilityResponse(
                request_id=request.id,
                ability_name="weather",
                action=request.action,
                success=True,
                message=f"Weather in {location}: {weather_data['description']}",
                data=weather_data,
            )
        except Exception as e:
            return AbilityResponse(
                request_id=request.id,
                ability_name="weather",
                action=request.action,
                success=False,
                error=str(e),
            )
    
    def get_supported_actions(self) -> list[str]:
        """Actions this ability can handle."""
        return ["get_weather", "weather_forecast", "current_weather"]
    
    async def _fetch_weather(self, location: str, units: str) -> dict:
        """Fetch weather from API."""
        # Implementation details
        pass
```

### Step 2: Register the Ability

```python
from bruno_core.base import BaseAssistant

# Create and register
weather = WeatherAbility()
await assistant.register_ability(weather)
```

## Ability Lifecycle

### Initialization

```python
class MyAbility(BaseAbility):
    async def initialize(self):
        """Called when ability is registered."""
        await super().initialize()
        # Your setup code
        self.api_client = ApiClient()
        self.cache = {}
```

### Shutdown

```python
    async def shutdown(self):
        """Called when ability is unregistered."""
        # Cleanup code
        await self.api_client.close()
        await super().shutdown()
```

### Health Check

```python
    async def health_check(self) -> dict:
        """Check if ability is healthy."""
        health = await super().health_check()
        health["api_status"] = await self.api_client.ping()
        return health
```

## Advanced Features

### Custom Validation

```python
class ValidatedAbility(BaseAbility):
    def validate_request(self, request: AbilityRequest) -> bool:
        """Custom validation logic."""
        if not super().validate_request(request):
            return False
        
        # Custom checks
        location = request.parameters.get("location")
        if not location or len(location) < 2:
            return False
        
        return True
```

### Rollback Support

```python
class TransactionalAbility(BaseAbility):
    async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
        # Store rollback info
        self.last_action = {
            "type": request.action,
            "data": {"old_value": current_value},
        }
        
        # Execute
        result = await self._do_action(request)
        return result
    
    async def rollback(self, request: AbilityRequest) -> None:
        """Undo the last action."""
        if self.last_action:
            await self._restore(self.last_action["data"])
```

### State Management

```python
class StatefulAbility(BaseAbility):
    def __init__(self):
        super().__init__()
        self.state = {}
    
    async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
        user_id = request.user_id
        
        # Get user-specific state
        user_state = self.state.get(user_id, {})
        
        # Update state
        user_state["last_action"] = request.action
        self.state[user_id] = user_state
        
        # Execute
        return await self._process(request, user_state)
```

## Ability Patterns

### API Integration

```python
import aiohttp

class ApiAbility(BaseAbility):
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.session = None
    
    async def initialize(self):
        await super().initialize()
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
    
    async def shutdown(self):
        if self.session:
            await self.session.close()
        await super().shutdown()
    
    async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
        async with self.session.get(self.api_url) as resp:
            data = await resp.json()
        
        return AbilityResponse(
            request_id=request.id,
            ability_name=self._metadata.name,
            action=request.action,
            success=True,
            data=data,
        )
```

### Database Operations

```python
import asyncpg

class DatabaseAbility(BaseAbility):
    def __init__(self, db_url: str):
        super().__init__()
        self.db_url = db_url
        self.pool = None
    
    async def initialize(self):
        await super().initialize()
        self.pool = await asyncpg.create_pool(self.db_url)
    
    async def shutdown(self):
        if self.pool:
            await self.pool.close()
        await super().shutdown()
    
    async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
        query = request.parameters.get("query")
        
        async with self.pool.acquire() as conn:
            result = await conn.fetch(query)
        
        return AbilityResponse(
            request_id=request.id,
            ability_name=self._metadata.name,
            action=request.action,
            success=True,
            data={"rows": [dict(r) for r in result]},
        )
```

### File Operations

```python
import aiofiles

class FileAbility(BaseAbility):
    async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
        action = request.action
        file_path = request.parameters.get("path")
        
        if action == "read":
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
            return self._success_response(request, {"content": content})
        
        elif action == "write":
            content = request.parameters.get("content")
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(content)
            return self._success_response(request, {"written": True})
```

### Scheduled Tasks

```python
import asyncio

class ScheduledAbility(BaseAbility):
    def __init__(self):
        super().__init__()
        self.tasks = {}
    
    async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
        action = request.action
        
        if action == "schedule":
            delay = request.parameters.get("delay", 60)
            task_id = str(uuid.uuid4())
            
            task = asyncio.create_task(self._run_after_delay(delay, request))
            self.tasks[task_id] = task
            
            return self._success_response(request, {"task_id": task_id})
        
        elif action == "cancel":
            task_id = request.parameters.get("task_id")
            task = self.tasks.get(task_id)
            if task:
                task.cancel()
                return self._success_response(request, {"cancelled": True})
    
    async def _run_after_delay(self, delay: int, original_request: AbilityRequest):
        await asyncio.sleep(delay)
        # Execute the scheduled action
        await self._do_scheduled_action(original_request)
```

## Plugin Registration

### Via Entry Points

```python
# setup.py
from setuptools import setup

setup(
    name="my-bruno-abilities",
    packages=["my_abilities"],
    entry_points={
        "bruno.abilities": [
            "weather = my_abilities.weather:WeatherAbility",
            "timer = my_abilities.timer:TimerAbility",
            "notes = my_abilities.notes:NotesAbility",
        ]
    }
)
```

### Manual Registration

```python
from bruno_core.registry import AbilityRegistry

registry = AbilityRegistry()
registry.register(
    name="weather",
    plugin_class=WeatherAbility,
    version="1.0.0",
    metadata={"category": "utilities"}
)
```

## Testing Abilities

```python
import pytest
from bruno_core.models import AbilityRequest

@pytest.mark.asyncio
async def test_weather_ability():
    ability = WeatherAbility()
    await ability.initialize()
    
    request = AbilityRequest(
        ability_name="weather",
        action="get_weather",
        parameters={"location": "London", "units": "celsius"},
        user_id="test-user",
    )
    
    response = await ability.execute(request)
    
    assert response.success is True
    assert "weather" in response.data
    
    await ability.shutdown()
```

## Best Practices

### 1. Use Type Hints

```python
async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
    location: str = request.parameters.get("location")
    units: str = request.parameters.get("units", "celsius")
```

### 2. Validate Input

```python
def validate_request(self, request: AbilityRequest) -> bool:
    if not super().validate_request(request):
        return False
    
    location = request.parameters.get("location")
    if not location or not isinstance(location, str):
        return False
    
    return True
```

### 3. Handle Errors Gracefully

```python
async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
    try:
        result = await self._do_work(request)
        return self._success_response(request, result)
    except ApiError as e:
        logger.error("api_error", error=str(e))
        return self._error_response(request, f"API error: {str(e)}")
    except Exception as e:
        logger.error("unexpected_error", error=str(e))
        return self._error_response(request, "An unexpected error occurred")
```

### 4. Log Appropriately

```python
from bruno_core.utils.logging import get_logger

logger = get_logger(__name__)

async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
    logger.info("ability_executing", 
                ability=self._metadata.name,
                action=request.action,
                user_id=request.user_id)
    
    result = await self._do_work(request)
    
    logger.info("ability_executed",
                ability=self._metadata.name,
                success=True)
    
    return self._success_response(request, result)
```

### 5. Document Thoroughly

```python
class DocumentedAbility(BaseAbility):
    """
    A well-documented ability.
    
    This ability does X, Y, and Z. It requires API credentials
    and has the following limitations:
    - Rate limit: 100 requests/hour
    - Max payload: 1MB
    
    Example:
        >>> ability = DocumentedAbility(api_key="...")
        >>> await ability.initialize()
        >>> response = await ability.execute(request)
    """
    
    async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
        """
        Execute the ability action.
        
        Args:
            request: Ability request with action and parameters
        
        Returns:
            AbilityResponse with success status and data
        
        Raises:
            ApiError: If API call fails
            ValidationError: If parameters are invalid
        """
        pass
```

## Examples

See the [examples directory](../../examples/custom_ability.py) for complete, working examples of:
- Basic ability
- API integration ability
- Database ability
- File operations ability
- Scheduled task ability

## Troubleshooting

### Ability Not Detected

Ensure:
1. Ability is registered with assistant
2. get_supported_actions() returns correct action names
3. Action keywords appear in user messages

### Validation Failures

Check:
1. Required parameters are present
2. Parameter types match metadata
3. allowed_values constraints are met

### Execution Errors

Debug by:
1. Adding logging statements
2. Checking health_check() output
3. Testing with simple inputs first
4. Reviewing error messages in response

---

For more examples, see the [examples directory](../../examples/).
