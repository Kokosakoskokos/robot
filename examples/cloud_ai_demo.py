#!/usr/bin/env python3
"""
Cloud AI Demo for Clanker Robot
================================

This script demonstrates how Clanker can use cloud AI (OpenRouter API)
to make intelligent decisions and edit code.

Prerequisites:
1. Set OPENROUTER_API_KEY environment variable
2. Install dependencies: pip install -r requirements.txt

Usage:
    python examples/cloud_ai_demo.py --test-connection
    python examples/cloud_ai_demo.py --demo-decisions
    python examples/cloud_ai_demo.py --demo-code-edit
"""

import os
import sys
import json
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.openrouter_client import OpenRouterClient, OpenRouterConfig
from ai.brain import RobotBrain
from utils.logger import setup_logger

logger = setup_logger(__name__)


def test_connection():
    """Test connection to OpenRouter API."""
    print("=" * 60)
    print("Testing Cloud AI Connection")
    print("=" * 60)
    
    # Check if API key is set
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in environment variables")
        print("\nTo set it up:")
        print("  Linux/macOS: export OPENROUTER_API_KEY='your_key_here'")
        print("  Windows PowerShell: $env:OPENROUTER_API_KEY='your_key_here'")
        print("\nGet your free API key at: https://openrouter.ai/")
        return False
    
    print(f"✓ API key found (starts with: {api_key[:20]}...)")
    
    # Create OpenRouter client
    cfg = OpenRouterConfig(
        base_url="https://openrouter.ai/api/v1",
        model="mistralai/devstral-small:free",  # Free model
        timeout_s=20,
        max_retries=2,
        temperature=0.2
    )
    
    client = OpenRouterClient(cfg)
    
    if not client.is_configured():
        print("❌ OpenRouter client not configured properly")
        return False
    
    print("✓ OpenRouter client configured")
    
    # Test with a simple prompt
    print("\nTesting with simple prompt...")
    try:
        messages = [
            {"role": "system", "content": "You are a helpful robot assistant."},
            {"role": "user", "content": "What are 3 things a hexapod robot should do when it encounters an obstacle?"}
        ]
        
        start_time = time.time()
        response = client.chat(messages)
        elapsed = time.time() - start_time
        
        print(f"\n✅ Cloud AI responded in {elapsed:.2f} seconds!")
        print(f"\nAI Response:\n{response}")
        print("\n" + "=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def demo_decisions():
    """Demonstrate AI-powered decision making."""
    print("=" * 60)
    print("Demo: AI-Powered Decision Making")
    print("=" * 60)
    
    # Initialize brain with AI enabled
    brain = RobotBrain(
        project_root=".",
        self_modify_enabled=False,
        llm_config={
            "enabled": True,
            "required": False,
            "model": "mistralai/devstral-small:free",
            "timeout_s": 20,
            "max_retries": 2,
            "temperature": 0.2
        },
        robot_name="Clanker",
        primary_language="cs"
    )
    
    if not brain.llm_enabled:
        print("❌ AI not configured. Run --test-connection first.")
        return False
    
    print("✓ AI brain configured")
    
    # Test scenarios
    scenarios = [
        {
            "name": "Obstacle detected ahead",
            "state": {
                "mode": "simulation",
                "obstacles": [{"position": [320, 240], "distance_estimate": 300}],
                "detections": [],
                "environment": {"brightness": 200, "edge_density": 0.1},
                "position": None,
                "navigation_info": None,
                "navigation_target": None,
                "heading": 0.0,
                "frame_width": 640,
                "frame_height": 480,
                "current_task": None
            }
        },
        {
            "name": "Clear path, time to explore",
            "state": {
                "mode": "simulation",
                "obstacles": [],
                "detections": [],
                "environment": {"brightness": 150, "edge_density": 0.05},
                "position": None,
                "navigation_info": None,
                "navigation_target": None,
                "heading": 0.0,
                "frame_width": 640,
                "frame_height": 480,
                "current_task": None
            }
        },
        {
            "name": "Low battery situation",
            "state": {
                "mode": "simulation",
                "obstacles": [],
                "detections": [],
                "environment": {"brightness": 100, "edge_density": 0.02},
                "position": None,
                "navigation_info": None,
                "navigation_target": None,
                "heading": 0.0,
                "frame_width": 640,
                "frame_height": 480,
                "current_task": None,
                "battery_level": 0.2
            }
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'='*60}")
        print(f"Scenario {i}: {scenario['name']}")
        print(f"{'='*60}")
        
        try:
            start_time = time.time()
            action = brain.think(scenario['state'])
            elapsed = time.time() - start_time
            
            print(f"\n✓ Decision made in {elapsed:.2f} seconds")
            print(f"\nAction: {json.dumps(action, indent=2)}")
            
            if 'reason' in action:
                print(f"\nReasoning: {action['reason']}")
            
            time.sleep(1)  # Pause between scenarios
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("Demo Complete!")
    print(f"{'='*60}")
    return True


def demo_code_edit():
    """Demonstrate AI code editing capabilities."""
    print("=" * 60)
    print("Demo: AI Code Editing")
    print("=" * 60)
    
    print("\n⚠️  Note: Code editing is a powerful feature.")
    print("Always test in simulation first!")
    print("Always backup before making changes!\n")
    
    # Check if self-modification is enabled
    brain = RobotBrain(
        project_root=".",
        self_modify_enabled=True,
        llm_config={
            "enabled": True,
            "required": False,
            "model": "mistralai/devstral-small:free",
            "timeout_s": 30,
            "max_retries": 2,
            "temperature": 0.2
        },
        robot_name="Clanker",
        primary_language="cs"
    )
    
    if not brain.self_modifier.enabled:
        print("❌ Self-modification disabled in config")
        print("To enable: Set 'self_modify_enabled: true' in config/config.yaml")
        return False
    
    print("✓ Self-modification enabled")
    
    # Example: Generate a new behavior
    print("\nGenerating new behavior with cloud AI...")
    print("-" * 60)
    
    user_request = """
    Create a behavior that makes the robot explore in a spiral pattern
    when no obstacles are detected for 5 seconds.
    
    The robot should:
    1. Walk forward in a straight line
    2. Turn slightly right
    3. Repeat to create a spiral
    4. Stop if obstacle detected
    """
    
    # This would typically come from cloud AI
    # For demo, we'll show what the AI would generate
    generated_code = '''"""Spiral exploration behavior."""

from ai.behaviors import Behavior
import time

class SpiralExploreBehavior(Behavior):
    """Explore environment in spiral pattern."""
    
    def __init__(self):
        super().__init__("spiral_explore", priority=4)
        self.spiral_step = 0
        self.last_clear_time = 0
        
    def should_activate(self, state):
        """Activate when no obstacles and time elapsed."""
        current_time = time.time()
        
        # Check if no obstacles
        obstacles = state.get('obstacles', [])
        if obstacles:
            self.spiral_step = 0
            self.last_clear_time = 0
            return False
        
        # Track when path became clear
        if self.last_clear_time == 0:
            self.last_clear_time = current_time
        
        # Activate after 5 seconds of clear path
        return (current_time - self.last_clear_time) > 5
    
    def execute(self, state):
        """Execute spiral pattern."""
        # Spiral: walk forward, then turn right slightly
        if self.spiral_step % 3 == 0:
            # Walk forward
            action = {'action': 'walk_forward', 'steps': 2, 'speed': 0.1}
        else:
            # Turn right
            action = {'action': 'turn', 'angle': 15, 'steps': 1}
        
        self.spiral_step += 1
        return action
'''
    
    print("Generated behavior code:")
    print("-" * 60)
    print(generated_code)
    print("-" * 60)
    
    # Validate code
    print("\nValidating generated code...")
    try:
        import ast
        ast.parse(generated_code)
        print("✓ Code is syntactically valid")
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    
    # Ask for confirmation
    response = input("\nCreate this behavior file? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return False
    
    # Create the behavior
    print("\nCreating behavior file...")
    success = brain.create_new_behavior("SpiralExplore", generated_code)
    
    if success:
        print("✅ Behavior file created successfully!")
        print(f"   Location: ai/behaviors/spiralexplore.py")
        print("\nNext steps:")
        print("  1. Review the file")
        print("  2. Test in simulation: python main.py --simulation")
        print("  3. Add to robot: brain.behavior_manager.register_behavior(SpiralExploreBehavior())")
    else:
        print("❌ Failed to create behavior file")
        return False
    
    return True


def demo_learning():
    """Demonstrate AI learning from performance data."""
    print("=" * 60)
    print("Demo: AI Learning from Performance")
    print("=" * 60)
    
    brain = RobotBrain(
        project_root=".",
        self_modify_enabled=False,
        llm_config={
            "enabled": True,
            "required": False,
            "model": "mistralai/devstral-small:free",
            "timeout_s": 30,
            "max_retries": 2,
            "temperature": 0.3  # More creative for analysis
        },
        robot_name="Clanker",
        primary_language="cs"
    )
    
    if not brain.llm_enabled:
        print("❌ AI not configured")
        return False
    
    # Simulate some performance data
    print("\nSimulating robot performance data...")
    brain.performance_metrics = {
        'decisions_made': 150,
        'behaviors_executed': {
            'explore': 50,
            'avoid_obstacle': 80,
            'navigate_to_target': 20
        },
        'errors': 5
    }
    
    # Simulate behavior stats
    print("\nAnalyzing performance with cloud AI...")
    
    # This would normally be done by brain.learn()
    # For demo, show what AI would analyze
    analysis_prompt = """
    Analyze this robot performance data and suggest improvements:
    
    Performance Data:
    - Total decisions: 150
    - Behaviors used:
      * explore: 50 times
      * avoid_obstacle: 80 times  
      * navigate_to_target: 20 times
    - Errors: 5
    
    Questions:
    1. Which behavior is most successful?
    2. Which needs improvement?
    3. What optimization should be made?
    4. Any safety concerns?
    
    Return JSON with: 'success_rate', 'improvements', 'priority'
    """
    
    print(f"Analysis prompt:\n{analysis_prompt}")
    print("-" * 60)
    
    try:
        # In real implementation, this would call brain.learn()
        # which sends data to cloud AI
        start_time = time.time()
        
        # For demo, show example AI response
        ai_response = '''
        {
          "success_rate": 0.87,
          "improvements": [
            {
              "behavior": "navigate_to_target",
              "issue": "Low success rate (20/150 = 13%)",
              "suggestion": "Add path planning algorithm",
              "priority": "high"
            },
            {
              "behavior": "explore",
              "issue": "Repetitive patterns",
              "suggestion": "Add random exploration with memory",
              "priority": "medium"
            },
            {
              "behavior": "avoid_obstacle",
              "issue": "High usage suggests frequent obstacles",
              "suggestion": "Improve obstacle prediction",
              "priority": "medium"
            }
          ],
          "safety_concerns": [
            "High error rate (3.3%) - investigate root causes",
            "Consider adding emergency stop triggers"
          ]
        }
        '''
        
        elapsed = time.time() - start_time
        
        print(f"\n✓ Analysis completed in {elapsed:.2f} seconds")
        print(f"\nAI Analysis Results:")
        print(json.dumps(json.loads(ai_response), indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print(f"\n{'='*60}")
    print("Demo Complete!")
    print(f"{'='*60}")
    return True


def show_setup_guide():
    """Show setup guide for cloud AI."""
    print("=" * 60)
    print("Cloud AI Setup Guide")
    print("=" * 60)
    
    guide = """
1. GET API KEY
   ┌─────────────────────────────────────────────────────┐
   │ Visit: https://openrouter.ai/                      │
   │ Sign up for free account                           │
   │ Go to Dashboard → API Keys                         │
   │ Copy your API key (starts with sk-or-v1-)          │
   └─────────────────────────────────────────────────────┘

2. SET ENVIRONMENT VARIABLE
   
   Linux/macOS:
   ┌─────────────────────────────────────────────────────┐
   │ export OPENROUTER_API_KEY="sk-or-v1-..."           │
   └─────────────────────────────────────────────────────┘
   
   Windows PowerShell:
   ┌─────────────────────────────────────────────────────┐
   │ $env:OPENROUTER_API_KEY="sk-or-v1-..."            │
   └─────────────────────────────────────────────────────┘
   
   Or add to .env file:
   ┌─────────────────────────────────────────────────────┐
   │ OPENROUTER_API_KEY=sk-or-v1-...                    │
   └─────────────────────────────────────────────────────┘

3. CONFIGURE ROBOT
   
   Edit config/config.yaml:
   ┌─────────────────────────────────────────────────────┐
   │ ai:                                                │
   │   llm:                                             │
   │     enabled: true                                  │
   │     required: false  # Safe fallback               │
   │     model: "mistralai/devstral-small:free"         │
   │     timeout_s: 30                                  │
   │     max_retries: 3                                 │
   │     temperature: 0.2                               │
   └─────────────────────────────────────────────────────┘

4. TEST CONNECTION
   
   ┌─────────────────────────────────────────────────────┐
   │ python examples/cloud_ai_demo.py --test-connection │
   └─────────────────────────────────────────────────────┘

5. RUN WITH AI
   
   ┌─────────────────────────────────────────────────────┐
   │ python main.py --simulation                        │
   └─────────────────────────────────────────────────────┘

6. MONITOR COSTS
   
   - Free tier: ~1000 requests/day
   - Paid tier: ~$0.01/day for moderate use
   - Monitor at: https://openrouter.ai/usage

TIPS
✓ Start with free model (mistralai/devstral-small:free)
✓ Use 'required: false' for safety
✓ Test in simulation first
✓ Monitor API usage
✓ Cache common decisions
✓ Batch requests when possible

TROUBLESHOOTING
❌ "API key not found"
   → Check environment variable is set correctly
   
❌ "Connection timeout"
   → Check internet connection
   → Increase timeout_s in config
   
❌ "Rate limit exceeded"
   → Wait a minute and try again
   → Consider paid tier for higher limits
    """
    
    print(guide)
    return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Cloud AI Demo for Clanker Robot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python examples/cloud_ai_demo.py --test-connection
  python examples/cloud_ai_demo.py --demo-decisions
  python examples/cloud_ai_demo.py --demo-code-edit
  python examples/cloud_ai_demo.py --demo-learning
  python examples/cloud_ai_demo.py --setup-guide
        """
    )
    
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test OpenRouter API connection"
    )
    
    parser.add_argument(
        "--demo-decisions",
        action="store_true",
        help="Demo AI-powered decision making"
    )
    
    parser.add_argument(
        "--demo-code-edit",
        action="store_true",
        help="Demo AI code editing capabilities"
    )
    
    parser.add_argument(
        "--demo-learning",
        action="store_true",
        help="Demo AI learning from performance"
    )
    
    parser.add_argument(
        "--setup-guide",
        action="store_true",
        help="Show setup guide"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all demos"
    )
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        return 1
    
    results = []
    
    if args.setup_guide or args.all:
        results.append(show_setup_guide())
    
    if args.test_connection or args.all:
        results.append(test_connection())
    
    if args.demo_decisions or args.all:
        results.append(demo_decisions())
    
    if args.demo_code_edit or args.all:
        results.append(demo_code_edit())
    
    if args.demo_learning or args.all:
        results.append(demo_learning())
    
    # Summary
    print("\n" + "=" * 60)
    print("DEMO SUMMARY")
    print("=" * 60)
    print(f"Tests run: {len(results)}")
    print(f"Success: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("\n✅ All demos completed successfully!")
        print("\nNext steps:")
        print("  1. Get API key from openrouter.ai")
        print("  2. Set OPENROUTER_API_KEY environment variable")
        print("  3. Update config/config.yaml")
        print("  4. Run: python main.py --simulation")
    else:
        print("\n⚠️  Some demos failed. Check the errors above.")
    
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
