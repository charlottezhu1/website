from openai import OpenAI
from settings import DEEPSEEK_API_KEY, OPENAI_API_KEY
from app.utils.helpers import *
from app.utils.agent_components import (
    EmotionalStateTracker,
    ContextRetriever,
    format_context_for_prompt,
)
import json
import re

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
client_openai = OpenAI(api_key=OPENAI_API_KEY, base_url="https://api.openai.com/v1")


def deepseek_request(
    user_message: str,
    prompt: str = "You are a helpful assistant.",  # Prompt for task definition.
    model: str = "deepseek-chat",
    max_tokens: int = 1500,
) -> dict:
    """System prompt for character definition."""
    instruction = "You are going to roleplay as Charlotte. Keep your response short, concise, and casual. Follow the content and response style in the appeneded context and extra information. Avoid using dash or emoji."
    more_info = read_txt_file_from_directory()

    # Get relevant context from database
    context_retriever = ContextRetriever()
    context = context_retriever.retrieve_relevant_context(user_message)
    context_prompt = format_context_for_prompt(context)

    # Combine prompts
    system_prompt = instruction + "\n\n" + context_prompt + "\n\n" + more_info

    # Add emotional state instruction to the prompt
    emotional_instruction = """
    
    IMPORTANT: At the end of your response, include your current emotional state in this exact format:
    [EMOTION: emotion_name]
    [INTENSITY: 0.0-1.0] The higher the intensity, the more intense the emotion.

    For example:
    [EMOTION: happy]
    [INTENSITY: 0.8]

    Valid emotions: nervous, sad, happy, calm, excited, angry, relaxed, fearful, enthusiastic, satisfied, bored, lonely
    """

    final_prompt = system_prompt + emotional_instruction
    print("\n=== DEBUG: FINAL PROMPT ===")
    print(final_prompt)
    print("\n=== DEBUG: USER MESSAGE ===")
    print(user_message)

    """Make a request to LLM with a system prompt."""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": final_prompt},
                {"role": "user", "content": user_message},
            ],
            stream=False,
            max_tokens=max_tokens,
            temperature=0.1,
        )

        # Get the response content
        response_content = response.choices[0].message.content

        print("\n=== DEBUG: RAW RESPONSE ===")
        print(response_content)

        # Check if response content exists
        if not response_content:
            print("DEBUG: No response content generated")
            return {
                "reply": "No response generated",
                "emotion": "neutral",
                "intensity": 0.5,
            }

        # Parse emotional state from response
        emotion_data = parse_emotional_state(response_content)
        print("\n=== DEBUG: PARSED EMOTION DATA ===")
        print(emotion_data)

        # Remove emotional state markers from the response
        clean_response = remove_emotional_markers(response_content)
        print("\n=== DEBUG: CLEAN RESPONSE ===")
        print(clean_response)

        return {
            "reply": clean_response,
            "emotion": emotion_data["emotion"],
            "intensity": emotion_data["intensity"],
        }

    except Exception as e:
        print(f"\n=== DEBUG: ERROR IN DEEPSEEK REQUEST ===")
        print(f"Error: {str(e)}")
        return {
            "reply": f"GENERATION ERROR: {str(e)}",
            "emotion": "neutral",
            "intensity": 0.5,
        }


def parse_emotional_state(response: str) -> dict:
    """Parse emotional state from LLM response"""
    try:
        print("\n=== DEBUG: PARSING EMOTIONAL STATE ===")
        print("Input response:", response)

        # Extract emotion and intensity using regex
        emotion_match = re.search(r"\[EMOTION:\s*(\w+)\]", response, re.IGNORECASE)
        intensity_match = re.search(
            r"\[INTENSITY:\s*([0-9]*\.?[0-9]+)\]", response, re.IGNORECASE
        )

        print("Emotion match:", emotion_match.group(1) if emotion_match else None)
        print("Intensity match:", intensity_match.group(1) if intensity_match else None)

        emotion = emotion_match.group(1).lower() if emotion_match else "calm"
        intensity = float(intensity_match.group(1)) if intensity_match else 0.5

        # Validate emotion
        valid_emotions = [
            "nervous",
            "sad",
            "happy",
            "calm",
            "excited",
            "angry",
            "relaxed",
            "fearful",
            "enthusiastic",
            "satisfied",
            "bored",
            "lonely",
        ]

        # Map old emotions to new ones if they exist
        emotion_mapping = {
            "content": "satisfied",
            "focused": "calm",
            "thoughtful": "calm",
            "concerned": "nervous",
            "worried": "fearful",
            "frustrated": "angry",
            "surprised": "excited",
            "curious": "enthusiastic",
            "empathetic": "calm",
            "neutral": "calm",
        }

        print("Original emotion:", emotion)
        # If emotion is an old one, map it to new one
        if emotion in emotion_mapping:
            emotion = emotion_mapping[emotion]
            print("Mapped to:", emotion)
        elif emotion not in valid_emotions:
            emotion = "calm"  # Default to calm instead of neutral
            print("Invalid emotion, defaulting to:", emotion)

        # Clamp intensity between 0 and 1
        intensity = max(0.0, min(1.0, intensity))
        print("Final intensity:", intensity)

        result = {"emotion": emotion, "intensity": intensity}
        print("Final result:", result)
        return result

    except Exception as e:
        print(f"\n=== DEBUG: ERROR IN PARSE EMOTIONAL STATE ===")
        print(f"Error: {str(e)}")
        return {
            "emotion": "calm",
            "intensity": 0.5,
        }  # Default to calm instead of neutral


def remove_emotional_markers(response: str) -> str:
    """Remove emotional state markers from response"""
    # Remove emotion and intensity markers
    response = re.sub(r"\[EMOTION:\s*\w+\]", "", response, flags=re.IGNORECASE)
    response = re.sub(
        r"\[INTENSITY:\s*[0-9]*\.?[0-9]+\]", "", response, flags=re.IGNORECASE
    )

    # Clean up extra whitespace
    response = re.sub(r"\n\s*\n", "\n\n", response)
    response = response.strip()

    return response
