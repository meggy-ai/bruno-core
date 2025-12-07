"""
Custom Ability Example

Demonstrates how to create and use a custom ability.
"""

import asyncio
from bruno_core.base import BaseAssistant, BaseAbility
from bruno_core.models import (
    Message,
    MessageRole,
    AbilityMetadata,
    AbilityParameter,
    AbilityRequest,
    AbilityResponse,
)

# Use the mock implementations from basic_assistant
import sys
sys.path.append('.')
from examples.basic_assistant import MockLLM, MockMemory


class CalculatorAbility(BaseAbility):
    """A simple calculator ability."""
    
    def get_metadata(self) -> AbilityMetadata:
        return AbilityMetadata(
            name="calculator",
            description="Perform basic mathematical calculations",
            version="1.0.0",
            parameters=[
                AbilityParameter(
                    name="operation",
                    type="string",
                    description="Math operation to perform",
                    required=True,
                    allowed_values=["add", "subtract", "multiply", "divide"],
                ),
                AbilityParameter(
                    name="a",
                    type="number",
                    description="First number",
                    required=True,
                ),
                AbilityParameter(
                    name="b",
                    type="number",
                    description="Second number",
                    required=True,
                ),
            ],
            examples=[
                "Calculate 5 + 3",
                "What is 10 multiplied by 7?",
                "Divide 100 by 4",
            ],
        )
    
    async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
        """Execute the calculation."""
        operation = request.parameters.get("operation")
        a = float(request.parameters.get("a"))
        b = float(request.parameters.get("b"))
        
        try:
            if operation == "add":
                result = a + b
            elif operation == "subtract":
                result = a - b
            elif operation == "multiply":
                result = a * b
            elif operation == "divide":
                if b == 0:
                    raise ValueError("Cannot divide by zero")
                result = a / b
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            return AbilityResponse(
                request_id=request.id,
                ability_name="calculator",
                action=request.action,
                success=True,
                message=f"{a} {operation} {b} = {result}",
                data={"result": result, "operation": operation},
            )
        
        except Exception as e:
            return AbilityResponse(
                request_id=request.id,
                ability_name="calculator",
                action=request.action,
                success=False,
                error=str(e),
            )
    
    def get_supported_actions(self) -> list[str]:
        return ["calculate", "compute", "math"]


class TimerAbility(BaseAbility):
    """A simple timer ability that simulates setting timers."""
    
    def __init__(self):
        super().__init__()
        self.timers = {}
    
    def get_metadata(self) -> AbilityMetadata:
        return AbilityMetadata(
            name="timer",
            description="Set and manage timers",
            version="1.0.0",
            parameters=[
                AbilityParameter(
                    name="duration",
                    type="number",
                    description="Timer duration in seconds",
                    required=True,
                ),
                AbilityParameter(
                    name="label",
                    type="string",
                    description="Timer label",
                    required=False,
                ),
            ],
            examples=[
                "Set a timer for 5 minutes",
                "Timer for 30 seconds",
                "Set a cooking timer for 10 minutes",
            ],
        )
    
    async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
        """Set a timer."""
        duration = int(request.parameters.get("duration"))
        label = request.parameters.get("label", "Timer")
        
        timer_id = f"timer_{len(self.timers) + 1}"
        self.timers[timer_id] = {
            "duration": duration,
            "label": label,
            "user_id": request.user_id,
        }
        
        return AbilityResponse(
            request_id=request.id,
            ability_name="timer",
            action=request.action,
            success=True,
            message=f"✅ {label} set for {duration} seconds (ID: {timer_id})",
            data={"timer_id": timer_id, "duration": duration, "label": label},
        )
    
    def get_supported_actions(self) -> list[str]:
        return ["set_timer", "timer", "countdown"]


async def main():
    """Demo custom abilities."""
    
    print("🤖 Bruno Core - Custom Ability Example")
    print("=" * 50)
    
    # Initialize
    print("\n1️⃣  Setting up assistant...")
    llm = MockLLM()
    memory = MockMemory()
    assistant = BaseAssistant(llm=llm, memory=memory)
    await assistant.initialize()
    
    # Create and register abilities
    print("2️⃣  Creating custom abilities...")
    calculator = CalculatorAbility()
    timer = TimerAbility()
    
    await calculator.initialize()
    await timer.initialize()
    
    print("3️⃣  Registering abilities with assistant...")
    await assistant.register_ability(calculator)
    await assistant.register_ability(timer)
    
    print(f"✅ Registered {len(assistant.abilities)} abilities:")
    for name in assistant.abilities:
        ability = assistant.abilities[name]
        metadata = ability.get_metadata()
        print(f"   - {metadata.name}: {metadata.description}")
    
    # Test calculator ability directly
    print("\n4️⃣  Testing Calculator Ability (Direct)...")
    calc_request = AbilityRequest(
        ability_name="calculator",
        action="calculate",
        parameters={
            "operation": "add",
            "a": 15,
            "b": 27,
        },
        user_id="demo-user",
    )
    
    calc_response = await calculator.execute(calc_request)
    print(f"   Input: 15 + 27")
    print(f"   Result: {calc_response.message}")
    print(f"   Data: {calc_response.data}")
    
    # Test timer ability directly
    print("\n5️⃣  Testing Timer Ability (Direct)...")
    timer_request = AbilityRequest(
        ability_name="timer",
        action="set_timer",
        parameters={
            "duration": 300,  # 5 minutes
            "label": "Cooking Timer",
        },
        user_id="demo-user",
    )
    
    timer_response = await timer.execute(timer_request)
    print(f"   {timer_response.message}")
    
    # Test through assistant
    print("\n6️⃣  Testing Abilities Through Assistant...")
    print("   (In a real system, the assistant would detect these keywords)")
    
    messages = [
        "Please calculate 100 divided by 5",
        "Set a timer for 60 seconds",
    ]
    
    for msg in messages:
        print(f"\n   👤 User: {msg}")
        message = Message(role=MessageRole.USER, content=msg)
        response = await assistant.process_message(
            message=message,
            user_id="demo-user",
            conversation_id="demo-conv"
        )
        print(f"   🤖 Assistant: {response.text}")
        
        # Check if actions were executed
        if response.actions:
            print(f"   ✅ Executed {len(response.actions)} action(s)")
            for action in response.actions:
                print(f"      - {action.action_type}: {action.message}")
    
    # Show ability statistics
    print("\n7️⃣  Ability Statistics:")
    calc_health = await calculator.health_check()
    timer_health = await timer.health_check()
    print(f"   Calculator: {calc_health['status']}")
    print(f"   Timer: {timer_health['status']}, Active timers: {len(timer.timers)}")
    
    # Cleanup
    print("\n8️⃣  Shutting down...")
    await calculator.shutdown()
    await timer.shutdown()
    await assistant.shutdown()
    print("✅ Complete!")


if __name__ == "__main__":
    asyncio.run(main())
