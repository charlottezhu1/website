import os
import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, current_app
from app.utils.call_llm import deepseek_request
from app.utils.helpers import *
from app.utils.agent_components import (
    EmotionalStateTracker,
    ConversationManager,
    AutoObserver,
    populate_initial_data,
    analyze_conversation_for_save,
    generate_embedding,
    populate_embeddings_for_existing_memories,
)
from app import supabase_extension

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/analyze-conversation", methods=["POST"])
def analyze_conversation():
    """Analyze conversation and return auto-generated title, description, and quality score"""
    try:
        data = request.get_json()
        conversation = data.get("conversation", [])

        if not conversation:
            return jsonify({"error": "No conversation data provided"}), 400

        # Convert conversation format for analysis
        conversation_data = []
        for msg in conversation:
            conversation_data.append(
                {
                    "sender": msg.get("sender", "user"),
                    "text": msg.get("text", ""),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Analyze conversation
        analysis = analyze_conversation_for_save(conversation_data)

        return jsonify({"success": True, "analysis": analysis})

    except Exception as e:
        print(f"Error analyzing conversation: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/populate-initial-data", methods=["POST"])
def populate_data():
    """Populate the database with initial memory stream data"""
    try:
        populate_initial_data()
        return jsonify(
            {"success": True, "message": "Initial data populated successfully"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/chat", methods=["GET", "POST"])
def chat():
    is_dev = session.get("dev", False)
    response = supabase_extension.client.table("writings").select("id, title").execute()
    articles = response.data
    return render_template("chat.html", is_dev=is_dev, articles=articles)


@chat_bp.route("/send", methods=["POST"])
def send():
    try:
        data = request.get_json()
        print("Received JSON:", data)
        user_message = data.get("message", "").strip()
        prompt = data.get("prompt", "").strip()

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        # Call your language model with prompt and message
        print("generating reply...")
        response_data = deepseek_request(user_message, prompt=prompt)
        print(response_data)

        # Extract reply and emotional state
        reply = response_data.get("reply", "")
        emotion = response_data.get("emotion", "neutral")
        intensity = response_data.get("intensity", 0.5)

        # Store emotional state in database
        try:
            supabase_extension.client.table("emotional_states").insert(
                {
                    "emotion": emotion,
                    "intensity": intensity,
                    "trigger": f"User message: {user_message[:100]}...",
                    "conversation_context": f"Response to: {user_message[:100]}...",
                    "transition_from": "previous_state",  # You could track this more precisely
                }
            ).execute()
        except Exception as e:
            print(f"Error storing emotional state: {e}")

        # Store conversation context in memory_stream with embedding
        try:
            # Generate embedding for the conversation context
            context_text = f"User: {user_message}\nCharlotte: {reply}"
            context_embedding = generate_embedding(context_text)

            # Store in memory_stream table
            supabase_extension.client.table("memory_stream").insert(
                {
                    "user_message": user_message,
                    "agent_response": reply,
                    "conversation_topic": "general",  # Could be extracted later
                    "context_embedding": context_embedding,
                    "emotional_context": emotion,
                    "importance_score": 0.5,  # Default importance
                    "is_active": True,
                }
            ).execute()
        except Exception as e:
            print(f"Error storing conversation context: {e}")

        return jsonify({"reply": reply, "emotion": emotion, "intensity": intensity})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/current-emotion", methods=["GET"])
def get_current_emotion():
    """Get the most recent emotional state"""
    try:
        response = (
            supabase_extension.client.table("emotional_states")
            .select("*")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            latest_emotion = response.data[0]
            return jsonify(
                {
                    "emotion": latest_emotion["emotion"],
                    "intensity": latest_emotion["intensity"],
                    "timestamp": latest_emotion["created_at"],
                }
            )
        else:
            # Return default state if no emotional data exists
            return jsonify(
                {
                    "emotion": "happy",
                    "intensity": 0.7,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    except Exception as e:
        print(f"Error getting current emotion: {e}")
        return jsonify(
            {
                "emotion": "neutral",
                "intensity": 0.5,
                "timestamp": datetime.now().isoformat(),
            }
        )


@chat_bp.route("/save", methods=["POST"])
def save():
    try:
        data = request.get_json()
        conversation = data.get("conversation", [])
        title = data.get("title", "")
        description = data.get("description", "")
        quality_score = data.get("quality_score", 0.8)

        print(f"Debug: Received data - conversation length: {len(conversation)}")
        print(f"Debug: Title: {title}")
        print(f"Debug: Description: {description}")
        print(f"Debug: Quality score: {quality_score}")

        if not conversation:
            return jsonify({"error": "No conversation data provided"}), 400

        # Convert conversation format for database storage
        conversation_data = []
        for i, msg in enumerate(conversation):
            conversation_data.append(
                {
                    "sender": msg.get("sender", "user"),
                    "text": msg.get("text", ""),
                    "timestamp": datetime.now().isoformat(),
                }
            )
            print(
                f"Debug: Message {i}: sender={msg.get('sender')}, text_length={len(msg.get('text', ''))}"
            )

        print(f"Debug: Processed conversation_data length: {len(conversation_data)}")

        # Save to database using ConversationManager
        conversation_manager = ConversationManager()
        conversation_id = conversation_manager.save_conversation(
            conversation_data=conversation_data,
            title=title,
            description=description,
            quality_score=quality_score,
        )

        # Auto-observe and learn from the conversation
        try:
            auto_observer = AutoObserver()
            insights = auto_observer.observe_conversation(
                conversation_data, quality_score
            )
            print(f"AutoObserver insights: {insights}")
        except Exception as e:
            print(f"Error in auto-observation: {e}")

        return jsonify(
            {
                "success": True,
                "conversation_id": conversation_id,
                "message": "Conversation saved to database successfully!",
                "insights_extracted": bool(insights),
            }
        )

    except Exception as e:
        print(f"Error in save route: {e}")
        print(f"Error type: {type(e)}")
        if hasattr(e, "args"):
            print(f"Error args: {e.args}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/saved-conversations", methods=["GET"])
def get_saved_conversations():
    """Get list of saved conversations"""
    try:
        response = (
            supabase_extension.client.table("saved_conversations")
            .select(
                "id, title, description, conversation_type, topics, quality_score, usage_count, created_at"
            )
            .eq("is_active", True)
            .order("created_at", desc=True)
            .execute()
        )

        return jsonify({"success": True, "conversations": response.data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/test-save", methods=["GET"])
def test_save():
    """Test endpoint to verify database connection and table structure"""
    try:
        # Test basic insert with minimal data
        test_data = {
            "title": "Test Conversation",
            "description": "Test description",
            "conversation_data": [
                {
                    "sender": "user",
                    "text": "Hello",
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            "quality_score": 0.5,
            "conversation_type": "casual",
            "topics": ["test"],
            "emotional_arc": {"emotions": ["neutral"], "overall_tone": "neutral"},
            "usage_count": 0,
        }

        print(f"Debug: Testing with data: {test_data}")

        response = (
            supabase_extension.client.table("saved_conversations")
            .insert(test_data)
            .execute()
        )

        print(f"Debug: Test response: {response}")

        if response.data:
            # Clean up test data
            supabase_extension.client.table("saved_conversations").delete().eq(
                "id", response.data[0]["id"]
            ).execute()
            return jsonify(
                {
                    "success": True,
                    "message": "Database connection and table structure are working",
                }
            )
        else:
            return jsonify({"error": "No data returned from test insert"}), 500

    except Exception as e:
        print(f"Test save error: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/test-table", methods=["GET"])
def test_table():
    """Test if the saved_conversations table exists and is accessible"""
    try:
        # Try to select from the table to see if it exists
        response = (
            supabase_extension.client.table("saved_conversations")
            .select("id")
            .limit(1)
            .execute()
        )
        print(f"Debug: Table test response: {response}")
        return jsonify(
            {
                "success": True,
                "message": "Table exists and is accessible",
                "data": response.data,
            }
        )
    except Exception as e:
        print(f"Table test error: {e}")
        return (
            jsonify(
                {
                    "error": str(e),
                    "message": "Table might not exist or there's a connection issue",
                }
            ),
            500,
        )


@chat_bp.route("/save-simple", methods=["POST"])
def save_simple():
    """Simplified save function with minimal data to test basic insert"""
    try:
        data = request.get_json()
        conversation = data.get("conversation", [])

        if not conversation:
            return jsonify({"error": "No conversation data provided"}), 400

        # Create minimal test data
        simple_data = {
            "title": f"Test {datetime.now().strftime('%H:%M:%S')}",
            "description": "Simple test",
            "conversation_data": [
                {
                    "sender": "user",
                    "text": "test",
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            "quality_score": 0.5,
            "conversation_type": "casual",
            "topics": ["test"],
            "emotional_arc": {"emotions": ["neutral"], "overall_tone": "neutral"},
            "usage_count": 0,
        }

        print(f"Debug: Simple save data: {simple_data}")

        # Try direct insert without ConversationManager
        response = (
            supabase_extension.client.table("saved_conversations")
            .insert(simple_data)
            .execute()
        )

        print(f"Debug: Simple save response: {response}")

        if response.data:
            return jsonify(
                {
                    "success": True,
                    "conversation_id": response.data[0]["id"],
                    "message": "Simple save successful!",
                }
            )
        else:
            return jsonify({"error": "No data returned from simple insert"}), 500

    except Exception as e:
        print(f"Simple save error: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/populate-embeddings", methods=["POST"])
def populate_embeddings():
    """Populate embeddings for existing memory stream data"""
    try:
        populate_embeddings_for_existing_memories()
        return jsonify(
            {"success": True, "message": "Embeddings populated successfully"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
