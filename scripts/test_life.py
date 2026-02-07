import sys
sys.path.append("/root/ai_assistant")
import config
from core.personality import PersonalityEngine
from core.life_cycle import AgeService

def test_life():
    print("--- 🧬 TESTING LIFE OS ---")
    
    # 1. Check Age
    birth = AgeService.get_birth_date()
    age = AgeService.get_age_days()
    print(f"🎂 Birth: {birth}")
    print(f"📅 Age: {age} days")
    
    # 2. Check Stage
    stage = AgeService.get_life_stage(config.persona_config)
    print(f"👶 Stage: {stage['name']} (Traits: {stage['data'].get('traits')})")
    
    # 3. Generate Prompt (Sample)
    prompt = PersonalityEngine.get_system_instructions()
    print("\n📝 Generated Prompt Snippet (Tail):")
    print(prompt[-300:]) # Show last 300 chars to see dynamic injection
    
    if "[DYNAMIC PERSONA: ACTIVE]" in prompt:
        print("\n✅ Dynamic Persona injected successfully.")
    else:
        print("\n❌ FAILED to inject persona.")

if __name__ == "__main__":
    test_life()
