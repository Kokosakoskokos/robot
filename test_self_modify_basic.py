#!/usr/bin/env python3
from ai.self_modify import SelfModifier
import json

def test_self_modify():
    modifier = SelfModifier(".")
    
    print("Testing analyze_self...")
    analysis = modifier.analyze_self()
    print(f"Total functions found: {analysis['total_functions']}")
    print(f"Total classes found: {analysis['total_classes']}")
    
    print("\nTesting find_optimization_opportunities...")
    opps = modifier.find_optimization_opportunities()
    print(f"Opportunities found: {len(opps)}")
    for opp in opps:
        print(f"- {opp['file']}: {opp['description']}")

if __name__ == "__main__":
    test_self_modify()
