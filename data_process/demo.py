#!/usr/bin/env python3
"""
Demo script showing the socket interface functionality
"""

import time
import json
from env_state import env_state


def demo_basic_functionality():
    """Demonstrate basic functionality without socket connection"""
    print("Mind-Daemon Socket Interface Demo")
    print("=" * 40)
    
    print("\n1. Testing Environment State Management:")
    
    # Update light state
    env_state.update_light_state(is_on=True, color_hex="#FF5733", lightness=80)
    print("✓ Light state updated")
    
    # Update music state  
    env_state.update_music_state(is_playing=True, name="Aria De Capo", type_="Relaxing")
    print("✓ Music state updated")
    
    # Update curtain state
    env_state.update_curtain_state(state=0)  # 0 = open
    print("✓ Curtain state updated")
    
    # Update scores
    env_state.update_scores(At=65, Ex=45, Re=75, St=35)
    print("✓ Scores updated")
    
    print("\n2. Current Basic Parameters:")
    basic_params = env_state.get_basic_params()
    print(json.dumps(basic_params, indent=2))
    
    print("\n3. Simulating Real-time Updates:")
    for i in range(5):
        # Simulate changing scores over time
        at_score = 50 + (i * 5)
        re_score = 70 - (i * 3)
        
        env_state.update_scores(At=at_score, Re=re_score)
        
        current_params = env_state.get_basic_params()
        print(f"\nUpdate {i+1}:")
        print(f"Attention: {current_params['Scores']['At']}")
        print(f"Relaxation: {current_params['Scores']['Re']}")
        
        time.sleep(1)
    
    print("\n4. Final State:")
    print(env_state.get_json_params())
    
    print("\n✓ Demo completed successfully!")
    print("\nTo use with real BCI data (MET/POW streams):")
    print("1. Start socket server: python3 test_system.py")
    print("2. Run socket interface: python3 socket_interface.py") 
    print("3. Connect BCI headset - scores will be derived from MET data automatically")
    print("4. The system now subscribes to 'met' and 'pow' streams instead of 'eeg'/'mot'")


if __name__ == "__main__":
    demo_basic_functionality()