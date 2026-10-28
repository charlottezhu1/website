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
    # DISABLED: Embedding functionality commented out to avoid large model dependency
    # generate_embedding,
    # populate_embeddings_for_existing_memories,
)
from app import supabase_extension

chat_bp = Blueprint("chat", __name__)

# Chat depends on Supabase (auth, memory, emotional state). Set to True to re-enable.
CHAT_ENABLED = False


@chat_bp.app_context_processor
def inject_chat_enabled():
    # show_funzzies: set True to bring back the Funzzies nav dropdown
    return {"chat_enabled": CHAT_ENABLED, "show_funzzies": False}


@chat_bp.before_request
def block_when_disabled():
    if not CHAT_ENABLED and request.endpoint != "chat.chat":
        return jsonify({"error": "Chat is currently disabled"}), 503


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
    if not CHAT_ENABLED:
        return render_template("chat.html", chat_disabled=True, articles=[])

    is_dev = session.get("dev", False)
    response = supabase_extension.client.table("writings").select("id, title").execute()
    articles = response.data

    # Get auth context for template
    is_authenticated = session.get("user_id") is not None
    current_user = {
        "id": session.get("user_id", ""),
        "email": session.get("user_email", ""),
        "username": session.get("username", ""),
        "role": session.get("user_role", ""),
        "role_description": session.get("user_role_description", "")
    }

    return render_template(
        "chat.html",
        is_dev=is_dev,
        articles=articles,
        is_authenticated=is_authenticated,
        current_user=current_user
    )


@chat_bp.route("/auth/login", methods=["POST"])
def login():
    """Authenticate user with email and password via Supabase Auth"""
    try:
        data = request.get_json()
        email = data.get("email", "").strip()
        password = data.get("password", "")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        # Authenticate with Supabase Auth
        try:
            auth_response = supabase_extension.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if not auth_response.user:
                return jsonify({"error": "Invalid credentials"}), 401

            user_id = auth_response.user.id

            # Fetch user profile to get role and username
            profile_response = (
                supabase_extension.client.table("user_profiles")
                .select("username, role, role_description")
                .eq("id", user_id)
                .execute()
            )

            if not profile_response.data:
                return jsonify({"error": "User profile not found"}), 404

            profile = profile_response.data[0]

            # Store in Flask session
            session["user_id"] = user_id
            session["user_email"] = auth_response.user.email
            session["username"] = profile["username"]
            session["user_role"] = profile["role"]
            session["user_role_description"] = profile["role_description"]
            session["access_token"] = auth_response.session.access_token

            print(f"✓ User logged in: {profile['username']} ({profile['role']})")

            return jsonify({
                "success": True,
                "user": {
                    "id": user_id,
                    "email": auth_response.user.email,
                    "username": profile["username"],
                    "role": profile["role"]
                }
            })

        except Exception as e:
            print(f"Supabase auth error: {e}")
            return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/auth/logout", methods=["POST"])
def logout():
    """Clear user session"""
    try:
        username = session.get("username", "Unknown")
        session.clear()
        print(f"✓ User logged out: {username}")
        return jsonify({"success": True})
    except Exception as e:
        print(f"Logout error: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/current-user", methods=["GET"])
def get_current_user():
    """Get current authenticated user info"""
    try:
        user_id = session.get("user_id")

        if not user_id:
            return jsonify({"authenticated": False})

        return jsonify({
            "authenticated": True,
            "user": {
                "id": session.get("user_id"),
                "email": session.get("user_email"),
                "username": session.get("username"),
                "role": session.get("user_role")
            }
        })
    except Exception as e:
        print(f"Error getting current user: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/send", methods=["POST"])
def send():
    try:
        data = request.get_json()
        print("Received JSON:", data)
        user_message = data.get("message", "").strip()
        prompt = data.get("prompt", "").strip()

        # Get user context from session
        user_id = session.get("user_id")
        user_role = session.get("user_role", "unknown")
        username = session.get("username", "someone")

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        # Inject user role context into prompt if authenticated
        if user_id and user_role:
            role_context = f"\n\n[Context: You are speaking with {username}, your {user_role}.]"
            prompt = prompt + role_context if prompt else role_context

        # Call your language model with prompt and message
        print(f"generating reply for user: {username} ({user_role})...")
        response_data = deepseek_request(user_message, prompt=prompt, username=username, user_id=user_id)
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
                    "user_id": user_id,  # NULL if not authenticated
                }
            ).execute()
            print(f"✓ Emotional state stored for user: {username}")
        except Exception as e:
            print(f"✗ Error storing emotional state: {e}")

        # Store conversation context in memory_stream (without embedding - disabled)
        try:
            # DISABLED: Embedding generation commented out to avoid large model dependency
            # context_text = f"User: {user_message}\nCharlotte: {reply}"
            # context_embedding = generate_embedding(context_text)

            # Store in memory_stream table (without embedding)
            supabase_extension.client.table("memory_stream").insert(
                {
                    "user_message": user_message,
                    "agent_response": reply,
                    "conversation_topic": "general",  # Could be extracted later
                    # "context_embedding": context_embedding,  # Disabled
                    "emotional_context": {"emotion": emotion, "intensity": intensity},  # JSONB format
                    "relevance_score": 0.5,  # Match schema column name
                    "user_id": user_id,  # NULL if not authenticated
                }
            ).execute()
            print(f"✓ Memory stored for {username}: {user_message[:30]}... → {reply[:30]}...")
        except Exception as e:
            print(f"✗ Error storing conversation context: {e}")

        return jsonify({"reply": reply, "emotion": emotion, "intensity": intensity})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/current-emotion", methods=["GET"])
def get_current_emotion():
    """Get the most recent emotional state (filtered by user if authenticated)"""
    try:
        user_id = session.get("user_id")

        # Strategy 1: Try to get user-specific emotional state
        if user_id:
            response = (
                supabase_extension.client.table("emotional_states")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if response.data:
                latest_emotion = response.data[0]
                return jsonify({
                    "emotion": latest_emotion["emotion"],
                    "intensity": latest_emotion["intensity"],
                    "timestamp": latest_emotion["created_at"],
                })

        # Strategy 2: If no user-specific data, get the most recent global state
        response = (
            supabase_extension.client.table("emotional_states")
            .select("*")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            latest_emotion = response.data[0]
            return jsonify({
                "emotion": latest_emotion["emotion"],
                "intensity": latest_emotion["intensity"],
                "timestamp": latest_emotion["created_at"],
            })

        # Strategy 3: Only use default if database is completely empty
        return jsonify({
            "emotion": "calm",
            "intensity": 0.7,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        print(f"Error getting current emotion: {e}")
        # On error, try to get ANY emotional state from database
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
                return jsonify({
                    "emotion": latest_emotion["emotion"],
                    "intensity": latest_emotion["intensity"],
                    "timestamp": latest_emotion["created_at"],
                })
        except:
            pass

        # Final fallback
        return jsonify({
            "emotion": "calm",
            "intensity": 0.7,
            "timestamp": datetime.now().isoformat(),
        })


@chat_bp.route("/chat-history", methods=["GET"])
def get_chat_history():
    """Get chat history for the authenticated user"""
    try:
        user_id = session.get("user_id")

        if not user_id:
            return jsonify({"messages": []})  # Return empty for unauthenticated

        # Get query parameters for pagination
        limit = request.args.get("limit", 50, type=int)  # Default 50 messages
        offset = request.args.get("offset", 0, type=int)

        # Fetch messages from memory_stream
        response = (
            supabase_extension.client.table("memory_stream")
            .select("user_message, agent_response, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=False)  # Oldest first for chat display
            .range(offset, offset + limit - 1)
            .execute()
        )

        # Format messages for frontend
        messages = []
        for item in response.data:
            # Add user message
            messages.append({
                "sender": "user",
                "text": item["user_message"],
                "timestamp": item["created_at"]
            })
            # Add agent response
            messages.append({
                "sender": "bot",
                "text": item["agent_response"],
                "timestamp": item["created_at"]
            })

        return jsonify({
            "success": True,
            "messages": messages,
            "count": len(messages)
        })

    except Exception as e:
        print(f"Error fetching chat history: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "messages": []
        }), 500


@chat_bp.route("/emotion-log", methods=["GET"])
def get_emotion_log():
    """Get recent emotional state history (filtered by user)"""
    try:
        limit = request.args.get("limit", 20, type=int)  # Default 20 entries
        query_user_id = request.args.get("user_id")  # Optional query param

        # Get user_id from query param or session
        user_id = query_user_id if query_user_id else session.get("user_id")

        # Build query with optional user filtering
        query = (
            supabase_extension.client.table("emotional_states")
            .select("emotion, intensity, trigger, conversation_context, created_at, user_id")
        )

        # Filter by user_id if provided
        if user_id:
            query = query.eq("user_id", user_id)

        response = query.order("created_at", desc=True).limit(limit).execute()

        return jsonify({
            "success": True,
            "emotions": response.data,
            "count": len(response.data),
            "filtered_by_user": user_id is not None
        })

    except Exception as e:
        print(f"Error getting emotion log: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/memory-log", methods=["GET"])
def get_memory_log():
    """Get recent memory stream history (filtered by user)"""
    try:
        limit = request.args.get("limit", 20, type=int)  # Default 20 entries
        query_user_id = request.args.get("user_id")  # Optional query param

        # Get user_id from query param or session
        user_id = query_user_id if query_user_id else session.get("user_id")

        # Build query with optional user filtering
        query = (
            supabase_extension.client.table("memory_stream")
            .select("user_message, agent_response, conversation_topic, emotional_context, created_at, user_id")
        )

        # Filter by user_id if provided
        if user_id:
            query = query.eq("user_id", user_id)

        response = query.order("created_at", desc=True).limit(limit).execute()

        return jsonify({
            "success": True,
            "memories": response.data,
            "count": len(response.data),
            "filtered_by_user": user_id is not None
        })

    except Exception as e:
        print(f"Error getting memory log: {e}")
        return jsonify({"error": str(e)}), 500


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


# DISABLED: Embedding functionality commented out to avoid large model dependency
# @chat_bp.route("/populate-embeddings", methods=["POST"])
# def populate_embeddings():
#     """Populate embeddings for existing memory stream data"""
#     try:
#         populate_embeddings_for_existing_memories()
#         return jsonify(
#             {"success": True, "message": "Embeddings populated successfully"}
#         )
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
