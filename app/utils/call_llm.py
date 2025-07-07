from openai import OpenAI
from settings import DEEPSEEK_API_KEY
from app.utils.helpers import *
from app.utils.agent_components import (
    EmotionalStateTracker,
    ContextRetriever,
    format_context_for_prompt,
)
import json
import re

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")


def deepseek_request(
    user_message: str,
    prompt: str = "You are a helpful assistant.",  # Prompt for task definition.
    model: str = "deepseek-chat",
    max_tokens: int = 1500,
) -> dict:
    """System prompt for character definition."""
    base_prompt = read_txt_file_from_directory()

    # Get relevant context from database
    context_retriever = ContextRetriever()
    context = context_retriever.retrieve_relevant_context(user_message)
    context_prompt = format_context_for_prompt(context)

    # Combine prompts
    system_prompt = base_prompt + "\n\n" + context_prompt + "\n\n" + prompt

    # Add emotional state instruction to the prompt
    emotional_instruction = """
    
IMPORTANT: At the end of your response, include your current emotional state in this exact format:
[EMOTION: emotion_name]
[INTENSITY: 0.0-1.0] The higher the intensity, the more intense the emotion.

For example:
[EMOTION: happy]
[INTENSITY: 0.8]

Valid emotions: happy, excited, content, calm, focused, thoughtful, concerned, worried, sad, frustrated, angry, surprised, curious, enthusiastic, empathetic, neutral
"""

    """Make a request to LLM with a system prompt."""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt + emotional_instruction},
                {"role": "user", "content": user_message},
            ],
            stream=False,
            max_tokens=max_tokens,
            temperature=0.7,
        )

        # Get the response content
        response_content = response.choices[0].message.content

        # Check if response content exists
        if not response_content:
            return {
                "reply": "No response generated",
                "emotion": "neutral",
                "intensity": 0.5,
            }

        # Parse emotional state from response
        emotion_data = parse_emotional_state(response_content)

        # Remove emotional state markers from the response
        clean_response = remove_emotional_markers(response_content)

        return {
            "reply": clean_response,
            "emotion": emotion_data["emotion"],
            "intensity": emotion_data["intensity"],
        }

    except Exception as e:
        return {
            "reply": f"GENERATION ERROR: {str(e)}",
            "emotion": "neutral",
            "intensity": 0.5,
        }


def parse_emotional_state(response: str) -> dict:
    """Parse emotional state from LLM response"""
    try:
        # Extract emotion and intensity using regex
        emotion_match = re.search(r"\[EMOTION:\s*(\w+)\]", response, re.IGNORECASE)
        intensity_match = re.search(
            r"\[INTENSITY:\s*([0-9]*\.?[0-9]+)\]", response, re.IGNORECASE
        )

        emotion = emotion_match.group(1).lower() if emotion_match else "neutral"
        intensity = float(intensity_match.group(1)) if intensity_match else 0.5

        # Validate emotion
        valid_emotions = [
            "happy",
            "excited",
            "content",
            "calm",
            "focused",
            "thoughtful",
            "concerned",
            "worried",
            "sad",
            "frustrated",
            "angry",
            "surprised",
            "curious",
            "enthusiastic",
            "empathetic",
            "neutral",
        ]

        if emotion not in valid_emotions:
            emotion = "neutral"

        # Clamp intensity between 0 and 1
        intensity = max(0.0, min(1.0, intensity))

        return {"emotion": emotion, "intensity": intensity}

    except Exception as e:
        print(f"Error parsing emotional state: {e}")
        return {"emotion": "neutral", "intensity": 0.5}


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
