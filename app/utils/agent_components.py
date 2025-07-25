import os
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import numpy as np
import threading
from typing import List
from app import supabase_extension
from sentence_transformers import SentenceTransformer

# Disable tokenizer parallelism to avoid fork warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Global variables for lazy loading
_embedding_model = None
_model_lock = threading.Lock()


def get_embedding_model():
    """Get the embedding model with lazy loading and thread safety"""
    global _embedding_model
    if _embedding_model is None:
        with _model_lock:
            # Double-check pattern to prevent race conditions
            if _embedding_model is None:
                _embedding_model = SentenceTransformer("intfloat/multilingual-e5-base")
    return _embedding_model


def generate_embedding(text: str) -> List[float]:
    """Generate embedding for text using Sentence Transformers intfloat/multilingual-e5-base model"""
    try:
        # Get model with lazy loading
        model = get_embedding_model()

        # E5 models require a "query: " prefix for optimal performance
        prefixed_text = f"query: {text}"

        # Generate embedding using sentence transformers
        embedding = model.encode(prefixed_text, convert_to_tensor=False)
        return embedding.tolist()
    except Exception as e:
        print(f"Error generating Sentence Transformer embedding: {e}")
        return []


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    import json

    # Handle case where embeddings might be stored as JSON strings
    if isinstance(a, str):
        try:
            a = json.loads(a)
        except:
            return 0.0
    if isinstance(b, str):
        try:
            b = json.loads(b)
        except:
            return 0.0

    if not a or not b:
        return 0.0

    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)

    if a.shape != b.shape or a.size == 0:
        return 0.0

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


class ConversationManager:
    """Manages conversation storage and retrieval for context building"""

    def __init__(self):
        self.saved_conversations_table = "saved_conversations"
        self.memory_stream_table = "memory_stream"

    def save_conversation(
        self,
        conversation_data: List[Dict],
        title: Optional[str] = None,
        description: Optional[str] = None,
        quality_score: float = 0.8,
    ) -> str:
        """Save a conversation to the database with embeddings"""
        try:
            # Analyze conversation for type and topics
            conversation_type = self._classify_conversation(conversation_data)
            topics = self._extract_topics(conversation_data)
            emotional_arc = self._extract_emotional_arc(conversation_data)

            # Generate title if not provided
            if not title:
                title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            # Generate embedding for the entire conversation
            conv_text = " ".join(
                [
                    f"{msg.get('text', '')} {msg.get('user_message', '')} {msg.get('agent_response', '')}"
                    for msg in conversation_data
                ]
            )
            embedding = generate_embedding(conv_text)

            # Insert into database
            response = (
                supabase_extension.client.table(self.saved_conversations_table)
                .insert(
                    {
                        "title": title,
                        "description": description
                        or f"Conversation about {', '.join(topics[:3])}",
                        "conversation_data": conversation_data,
                        "quality_score": quality_score,
                        "conversation_type": conversation_type,
                        "topics": topics,
                        "emotional_arc": emotional_arc,
                        "usage_count": 0,
                        "embedding": embedding,
                    }
                )
                .execute()
            )

            if response.data:
                return response.data[0]["id"]
            else:
                raise Exception("Failed to save conversation")

        except Exception as e:
            print(f"Error saving conversation: {e}")
            raise

    def get_relevant_conversations(
        self, user_message: str, limit: int = 3
    ) -> List[Dict]:
        """Retrieve relevant conversations based on embedding similarity"""
        try:
            print("\n=== DEBUG: SEARCHING WITH EMBEDDINGS ===")

            # Generate embedding for user message
            query_embedding = generate_embedding(user_message)

            # Get all conversations
            response = (
                supabase_extension.client.table(self.saved_conversations_table)
                .select("*")
                .eq("is_active", True)
                .execute()
            )

            if not response.data:
                print("No conversations found in database")
                return []

            # Calculate similarities and rank conversations
            conversations_with_scores = []
            for conv in response.data:
                conv_embedding = conv.get("embedding")
                if not conv_embedding:
                    continue

                # Calculate similarity score
                similarity = cosine_similarity(query_embedding, conv_embedding)

                # Apply quality and recency boosts
                quality_boost = float(conv.get("quality_score", 0.5))

                # Check recency
                messages = conv.get("conversation_data", [])
                recency_boost = 1.0
                if messages and len(messages) > 0:
                    last_msg = messages[-1]
                    if "timestamp" in last_msg:
                        try:
                            last_time = datetime.fromisoformat(last_msg["timestamp"])
                            time_diff = datetime.now() - last_time
                            if time_diff.days < 1:  # Within last 24 hours
                                recency_boost = 1.5
                        except (ValueError, TypeError):
                            pass

                # Calculate final score
                final_score = similarity * (1 + quality_boost) * recency_boost

                if final_score > 0:
                    conv["relevance_score"] = final_score
                    conversations_with_scores.append(conv)

            # Sort by relevance and return top results
            conversations_with_scores.sort(
                key=lambda x: x["relevance_score"], reverse=True
            )

            print(f"Found {len(conversations_with_scores)} relevant conversations")
            return conversations_with_scores[:limit]

        except Exception as e:
            print(f"Error retrieving relevant conversations: {e}")
            return []

    def get_conversation_context(self, user_message: str) -> str:
        """Get formatted conversation context for LLM prompt"""
        try:
            relevant_conversations = self.get_relevant_conversations(
                user_message, limit=2
            )

            if not relevant_conversations:
                return ""

            context_parts = []
            for conv in relevant_conversations:
                context_parts.append(
                    f"Relevant conversation about {', '.join(conv['topics'][:3])}:"
                )

                # Add key exchanges from the conversation
                messages = conv.get("conversation_data", [])
                for i, msg in enumerate(messages[:6]):  # Limit to 6 messages
                    sender = "User" if msg.get("sender") == "user" else "Charlotte"
                    context_parts.append(f"{sender}: {msg.get('text', '')}")

                context_parts.append("")  # Add spacing

            return "\n".join(context_parts)

        except Exception as e:
            print(f"Error getting conversation context: {e}")
            return ""

    def update_usage_count(self, conversation_id: str) -> None:
        """Update usage count for a conversation"""
        try:
            supabase_extension.client.table(self.saved_conversations_table).update(
                {"usage_count": supabase_extension.client.rpc("increment", {"x": 1})}
            ).eq("id", conversation_id).execute()
        except Exception as e:
            print(f"Error updating usage count: {e}")

    def _classify_conversation(self, conversation_data: List[Dict]) -> str:
        """Classify conversation type based on content"""
        text = " ".join([msg.get("text", "") for msg in conversation_data]).lower()

        keywords = {
            "academic": [
                "research",
                "study",
                "paper",
                "analysis",
                "methodology",
                "academic",
            ],
            "technical": [
                "code",
                "programming",
                "algorithm",
                "system",
                "implementation",
                "technical",
            ],
            "emotional": [
                "feel",
                "emotion",
                "sad",
                "happy",
                "excited",
                "worried",
                "love",
                "hate",
            ],
            "casual": [
                "hello",
                "how are you",
                "nice",
                "good",
                "great",
                "thanks",
                "thank you",
            ],
        }

        scores = {k: 0 for k in keywords.keys()}
        for conv_type, words in keywords.items():
            for word in words:
                if word in text:
                    scores[conv_type] += 1

        # Return the type with highest score, default to casual
        return (
            max(scores.keys(), key=lambda k: scores[k])
            if max(scores.values()) > 0
            else "casual"
        )

    def _extract_topics(self, conversation_data: List[Dict]) -> List[str]:
        """Extract main topics from conversation"""
        # Simple keyword extraction - could be enhanced with NLP
        text = " ".join([msg.get("text", "") for msg in conversation_data]).lower()

        # Common topics/keywords
        topics = []
        topic_keywords = {
            "research": ["research", "study", "paper", "experiment"],
            "coding": ["code", "programming", "algorithm", "bug", "function"],
            "personal": ["family", "friend", "home", "life", "experience"],
            "academic": ["university", "professor", "class", "assignment", "grade"],
            "technology": ["computer", "software", "app", "system", "technology"],
            "emotions": ["feel", "happy", "sad", "excited", "worried", "love"],
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in text for keyword in keywords):
                topics.append(topic)

        return topics[:5]  # Limit to 5 topics

    def _extract_emotional_arc(self, conversation_data: List[Dict]) -> Dict[str, Any]:
        """Extract emotional progression throughout conversation"""
        # Simple emotional analysis - could be enhanced
        emotions = []
        for msg in conversation_data:
            if msg.get("sender") == "bot":  # Only analyze Charlotte's responses
                text = msg.get("text", "").lower()

                # Simple emotion detection
                if any(
                    word in text for word in ["happy", "excited", "great", "wonderful"]
                ):
                    emotions.append("positive")
                elif any(
                    word in text for word in ["sad", "sorry", "unfortunate", "worried"]
                ):
                    emotions.append("negative")
                else:
                    emotions.append("neutral")

        return {
            "emotions": emotions,
            "overall_tone": (
                "positive"
                if emotions.count("positive") > emotions.count("negative")
                else (
                    "negative"
                    if emotions.count("negative") > emotions.count("positive")
                    else "neutral"
                )
            ),
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for matching"""
        # Simple keyword extraction - could be enhanced with NLP
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "me",
            "him",
            "her",
            "us",
            "them",
        }

        words = text.split()
        keywords = [
            word for word in words if word.lower() not in stop_words and len(word) > 2
        ]

        return keywords[:10]  # Limit to 10 keywords


class BackgroundManager:
    """Manages the agent's background knowledge with self-updating capabilities"""

    def __init__(self):
        self.table_name = "background_knowledge"

    def get_background_prompt(self) -> str:
        """Retrieve and format background knowledge for LLM prompt"""
        try:
            response = (
                supabase_extension.client.table(self.table_name)
                .select("*")
                .eq("is_active", True)
                .order("confidence_score", desc=True)
                .execute()
            )

            background_parts = []
            for item in response.data:
                background_parts.append(f"{item['knowledge_type']}: {item['content']}")

            return "You are Charlotte. " + " ".join(background_parts)

        except Exception as e:
            print(f"Error retrieving background: {e}")
            return "You are Charlotte, a master student at Stanford HCI group."

    def update_background(self, new_info: Dict[str, Any], confidence: float = 0.8):
        """Add or update background knowledge"""
        try:
            # Check if similar knowledge exists
            existing = (
                supabase_extension.client.table(self.table_name)
                .select("*")
                .eq("knowledge_type", new_info.get("type"))
                .eq("is_active", True)
                .execute()
            )

            if existing.data:
                # Update existing
                supabase_extension.client.table(self.table_name).update(
                    {
                        "content": new_info["content"],
                        "confidence_score": confidence,
                        "last_updated": datetime.now().isoformat(),
                        "source": new_info.get("source", "learned"),
                    }
                ).eq("id", existing.data[0]["id"]).execute()
            else:
                # Insert new
                supabase_extension.client.table(self.table_name).insert(
                    {
                        "knowledge_type": new_info["type"],
                        "content": new_info["content"],
                        "confidence_score": confidence,
                        "source": new_info.get("source", "learned"),
                    }
                ).execute()

        except Exception as e:
            print(f"Error updating background: {e}")


class ContextRetriever:
    """Retrieves relevant context from memory stream and database"""

    def __init__(self):
        self.memory_table = "memory_stream"

    def retrieve_relevant_context(
        self, user_message: str, limit: int = 5
    ) -> Dict[str, Any]:
        """Retrieve relevant context based on user message"""
        try:
            print("\n=== DEBUG: RETRIEVING CONTEXT ===")
            print("User message:", user_message)

            # Get recent conversations (last 24 hours)
            recent_context = self._get_recent_context(limit)
            print("Recent context count:", len(recent_context))

            # Get relevant historical context based on embedding similarity
            historical_context = self._get_historical_context(user_message, limit)
            print("Historical context count:", len(historical_context))

            # Generate conversation summary
            summary = self._generate_summary(recent_context + historical_context)
            print("Generated summary:", summary)

            return {
                "recent_context": recent_context,
                "historical_context": historical_context,
                "conversation_summary": summary,
            }

        except Exception as e:
            print(f"Error retrieving context: {e}")
            return {
                "recent_context": [],
                "historical_context": [],
                "conversation_summary": "",
            }

    def _get_recent_context(self, limit: int) -> List[Dict]:
        """Get recent conversation context"""
        try:
            yesterday = datetime.now() - timedelta(days=1)
            response = (
                supabase_extension.client.table(self.memory_table)
                .select("*")
                .gte("created_at", yesterday.isoformat())
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            print("\n=== DEBUG: RECENT CONTEXT ===")
            print(f"Found {len(response.data)} recent items")
            return response.data
        except Exception as e:
            print(f"Error getting recent context: {e}")
            return []

    def _get_historical_context(self, user_message: str, limit: int) -> List[Dict]:
        """Get historically relevant context based on embedding similarity"""
        try:
            print("\n=== DEBUG: HISTORICAL CONTEXT SEARCH ===")

            # Generate embedding for user message
            query_embedding = generate_embedding(user_message)

            # Get all memories
            response = (
                supabase_extension.client.table(self.memory_table).select("*").execute()
            )

            if not response.data:
                return []

            # Calculate similarities and rank memories
            memories_with_scores = []
            for memory in response.data:
                memory_text = f"{memory.get('user_message', '')} {memory.get('agent_response', '')}"
                memory_embedding = memory.get("embedding")

                if not memory_embedding:
                    # Generate embedding if not present
                    memory_embedding = generate_embedding(memory_text)
                    # Update memory with embedding
                    supabase_extension.client.table(self.memory_table).update(
                        {"embedding": memory_embedding}
                    ).eq("id", memory["id"]).execute()

                similarity = cosine_similarity(query_embedding, memory_embedding)

                if similarity > 0.5:  # Threshold for relevance
                    memory["similarity_score"] = similarity
                    memories_with_scores.append(memory)

            # Sort by similarity and return top results
            memories_with_scores.sort(key=lambda x: x["similarity_score"], reverse=True)

            print(f"Found {len(memories_with_scores)} relevant historical items")
            return memories_with_scores[:limit]

        except Exception as e:
            print(f"Error getting historical context: {e}")
            return []

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        # Remove common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "me",
            "him",
            "her",
            "us",
            "them",
        }

        # Split into words and filter
        words = text.split()
        keywords = [
            word for word in words if word.lower() not in stop_words and len(word) > 2
        ]

        return keywords[:5]  # Limit to top 5 keywords

    def _generate_summary(self, context_items: List[Dict]) -> str:
        """Generate a summary of the context"""
        if not context_items:
            return ""

        # Extract topics and themes
        topics = set()
        for item in context_items:
            if item.get("conversation_topic"):
                topics.add(item["conversation_topic"])

            # Extract potential topics from content
            content = f"{item.get('user_message', '')} {item.get('agent_response', '')}"
            keywords = self._extract_keywords(content.lower())
            topics.update(keywords)

        # Format summary
        topics_list = list(topics)[:3]  # Take top 3 topics
        if topics_list:
            return f"Previous discussions about: {', '.join(topics_list)}"
        return ""


class SpeechStyleRetriever:
    """Retrieves relevant speech patterns for style matching"""

    def __init__(self):
        self.table_name = "speech_patterns"

    def retrieve_speech_patterns(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve speech patterns based on conversation context"""
        try:
            # Determine conversation type from context
            conversation_type = self._classify_conversation(context)

            # Get relevant speech patterns
            patterns = self._get_patterns_by_type(conversation_type)

            # Get most effective patterns
            effective_patterns = self._get_effective_patterns(conversation_type)

            return {
                "tone": patterns.get("tone", "friendly"),
                "vocabulary": patterns.get("vocabulary_style", "conversational"),
                "response_length": patterns.get("response_length", "medium"),
                "examples": patterns.get("example_responses", []),
                "conversation_type": conversation_type,
            }

        except Exception as e:
            print(f"Error retrieving speech patterns: {e}")
            return {
                "tone": "friendly",
                "vocabulary": "conversational",
                "response_length": "medium",
                "examples": [],
                "conversation_type": "casual",
            }

    def _classify_conversation(self, context: Dict[str, Any]) -> str:
        """Classify conversation type based on context"""
        # Simple classification logic
        recent_context = context.get("recent_context", [])

        keywords = {
            "academic": ["research", "study", "paper", "analysis", "methodology"],
            "technical": [
                "code",
                "programming",
                "algorithm",
                "system",
                "implementation",
            ],
            "emotional": ["feel", "emotion", "sad", "happy", "excited", "worried"],
            "casual": ["hello", "how are you", "nice", "good", "great"],
        }

        # Count keyword matches
        scores = {k: 0 for k in keywords.keys()}
        for item in recent_context:
            text = (
                item.get("user_message", "") + " " + item.get("agent_response", "")
            ).lower()
            for conv_type, words in keywords.items():
                for word in words:
                    if word in text:
                        scores[conv_type] += 1

        # Return type with highest score
        return (
            max(scores.keys(), key=lambda k: scores[k])
            if any(scores.values())
            else "casual"
        )

    def _get_patterns_by_type(self, conversation_type: str) -> Dict[str, Any]:
        """Get speech patterns for specific conversation type"""
        try:
            response = (
                supabase_extension.client.table(self.table_name)
                .select("*")
                .eq("conversation_type", conversation_type)
                .order("effectiveness_score", desc=True)
                .limit(1)
                .execute()
            )

            return response.data[0] if response.data else {}
        except Exception as e:
            print(f"Error getting patterns: {e}")
            return {}

    def _get_effective_patterns(self, conversation_type: str) -> List[Dict]:
        """Get most effective patterns for conversation type"""
        try:
            response = (
                supabase_extension.client.table(self.table_name)
                .select("*")
                .eq("conversation_type", conversation_type)
                .gte("effectiveness_score", 0.7)
                .order("usage_count", desc=True)
                .limit(3)
                .execute()
            )

            return response.data
        except Exception as e:
            print(f"Error getting effective patterns: {e}")
            return []


class EmotionalStateTracker:
    """Tracks and manages emotional state over time"""

    def __init__(self):
        self.states_table = "emotional_states"
        self.triggers_table = "emotional_triggers"
        self.current_emotion = "happy"
        self.current_intensity = 0.7

    def update_emotion(self, conversation_context: Dict[str, Any]) -> None:
        """Update emotional state based on conversation context"""
        try:
            # Analyze conversation for emotional triggers
            emotion_change = self._analyze_emotional_triggers(conversation_context)

            # Calculate new emotional state
            new_emotion = self._calculate_new_emotion(emotion_change)
            new_intensity = self._calculate_new_intensity(emotion_change)

            # Record emotional state change
            self._record_emotional_state(new_emotion, new_intensity, emotion_change)

            # Update current state
            self.current_emotion = new_emotion
            self.current_intensity = new_intensity

        except Exception as e:
            print(f"Error updating emotion: {e}")

    def get_emotional_context(self) -> Dict[str, Any]:
        """Get current emotional context for LLM prompt"""
        try:
            # Get recent emotional history
            recent_states = self._get_recent_emotional_states(5)

            return {
                "current_emotion": self.current_emotion,
                "current_intensity": self.current_intensity,
                "emotional_history": recent_states,
                "emotional_tone": self._get_emotional_tone(),
            }

        except Exception as e:
            print(f"Error getting emotional context: {e}")
            return {
                "current_emotion": "happy",
                "current_intensity": 0.7,
                "emotional_history": [],
                "emotional_tone": "positive",
            }

    def _analyze_emotional_triggers(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze conversation for emotional triggers"""
        try:
            # Get all triggers
            response = (
                supabase_extension.client.table(self.triggers_table)
                .select("*")
                .execute()
            )

            triggers = response.data
            detected_triggers = []

            # Check recent context for triggers
            recent_context = context.get("recent_context", [])
            for item in recent_context:
                text = (
                    item.get("user_message", "") + " " + item.get("agent_response", "")
                ).lower()

                for trigger in triggers:
                    if trigger["trigger_value"].lower() in text:
                        detected_triggers.append(
                            {
                                "trigger": trigger["trigger_value"],
                                "emotion": trigger["emotion_induced"],
                                "intensity_change": trigger["intensity_change"],
                                "confidence": trigger["confidence_score"],
                            }
                        )

            return {
                "detected_triggers": detected_triggers,
                "strongest_trigger": (
                    max(detected_triggers, key=lambda x: x["confidence"])
                    if detected_triggers
                    else None
                ),
            }

        except Exception as e:
            print(f"Error analyzing triggers: {e}")
            return {"detected_triggers": [], "strongest_trigger": None}

    def _calculate_new_emotion(self, emotion_change: Dict[str, Any]) -> str:
        """Calculate new emotional state based on triggers"""
        strongest_trigger = emotion_change.get("strongest_trigger")

        if strongest_trigger:
            return strongest_trigger["emotion"]

        # Default: gradual return to baseline
        return "happy"

    def _calculate_new_intensity(self, emotion_change: Dict[str, Any]) -> float:
        """Calculate new emotional intensity"""
        strongest_trigger = emotion_change.get("strongest_trigger")

        if strongest_trigger:
            new_intensity = (
                self.current_intensity + strongest_trigger["intensity_change"]
            )
            return max(0.0, min(1.0, new_intensity))  # Clamp between 0 and 1

        # Gradual decay
        return max(0.3, self.current_intensity * 0.95)

    def _record_emotional_state(
        self, emotion: str, intensity: float, trigger_info: Dict[str, Any]
    ) -> None:
        """Record emotional state change in database"""
        try:
            supabase_extension.client.table(self.states_table).insert(
                {
                    "emotion": emotion,
                    "intensity": intensity,
                    "trigger": trigger_info.get("strongest_trigger", {}).get("trigger"),
                    "conversation_context": "Recent conversation",
                    "transition_from": self.current_emotion,
                }
            ).execute()

        except Exception as e:
            print(f"Error recording emotional state: {e}")

    def _get_recent_emotional_states(self, limit: int) -> List[Dict]:
        """Get recent emotional states"""
        try:
            response = (
                supabase_extension.client.table(self.states_table)
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            return response.data
        except Exception as e:
            print(f"Error getting recent states: {e}")
            return []

    def _get_emotional_tone(self) -> str:
        """Get emotional tone for LLM prompt"""
        positive_emotions = ["happy", "excited", "enthusiastic", "content"]
        negative_emotions = ["sad", "angry", "frustrated", "worried"]
        neutral_emotions = ["calm", "focused", "thoughtful"]

        if self.current_emotion in positive_emotions:
            return "positive"
        elif self.current_emotion in negative_emotions:
            return "negative"
        else:
            return "neutral"


def format_context_for_prompt(context: Dict[str, Any]) -> str:
    """Format context data for inclusion in LLM prompt"""
    if not context:
        return ""

    context_parts = []

    # Add recent context if available
    recent_context = context.get("recent_context", [])
    if recent_context:
        context_parts.append("Recent conversation context:")
        for item in recent_context[-3:]:  # Last 3 items
            if isinstance(item, dict):
                user_msg = item.get("user_message", "")
                agent_msg = item.get("agent_response", "")
                if user_msg or agent_msg:
                    if user_msg:
                        context_parts.append(f"User: {user_msg}")
                    if agent_msg:
                        context_parts.append(f"Assistant: {agent_msg}")
        context_parts.append("")

    # Add historical context if available
    historical_context = context.get("historical_context", [])
    if historical_context:
        context_parts.append("Relevant historical context:")
        for item in historical_context[:3]:  # First 3 items
            if isinstance(item, dict):
                user_msg = item.get("user_message", "")
                agent_msg = item.get("agent_response", "")
                if user_msg or agent_msg:
                    if user_msg:
                        context_parts.append(f"User: {user_msg}")
                    if agent_msg:
                        context_parts.append(f"Assistant: {agent_msg}")
        context_parts.append("")

    # Add summary if available
    summary = context.get("conversation_summary", "")  # Updated key name
    if summary:
        context_parts.append(f"Context summary: {summary}")
        context_parts.append("")

    return "\n".join(context_parts)


class AutoObserver:
    """Automatically observes and analyzes conversation patterns"""

    def __init__(self):
        self.observation_count = 0

    def observe_conversation(self, conversation_data: List[Dict]) -> Dict[str, Any]:
        """Analyze conversation and return insights"""
        self.observation_count += 1

        insights = {
            "conversation_length": len(conversation_data),
            "user_message_count": sum(
                1 for msg in conversation_data if msg.get("sender") == "user"
            ),
            "bot_message_count": sum(
                1 for msg in conversation_data if msg.get("sender") == "bot"
            ),
            "average_message_length": self._calculate_average_length(conversation_data),
            "conversation_topics": self._extract_topics(conversation_data),
            "emotional_tone": self._analyze_emotional_tone(conversation_data),
            "observation_id": self.observation_count,
        }

        return insights

    def _calculate_average_length(self, conversation_data: List[Dict]) -> float:
        """Calculate average message length"""
        if not conversation_data:
            return 0.0

        total_length = sum(len(msg.get("text", "")) for msg in conversation_data)
        return total_length / len(conversation_data)

    def _extract_topics(self, conversation_data: List[Dict]) -> List[str]:
        """Extract conversation topics"""
        # Simple keyword-based topic extraction
        text = " ".join([msg.get("text", "") for msg in conversation_data]).lower()

        topics = []
        topic_keywords = {
            "technology": ["code", "programming", "software", "computer", "tech"],
            "academic": ["research", "study", "paper", "analysis", "academic"],
            "personal": ["feel", "think", "believe", "experience", "life"],
            "casual": ["hello", "how", "nice", "good", "thanks"],
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in text for keyword in keywords):
                topics.append(topic)

        return topics if topics else ["general"]

    def _analyze_emotional_tone(self, conversation_data: List[Dict]) -> str:
        """Analyze emotional tone of conversation"""
        text = " ".join([msg.get("text", "") for msg in conversation_data]).lower()

        positive_words = [
            "happy",
            "excited",
            "great",
            "wonderful",
            "amazing",
            "love",
            "enjoy",
        ]
        negative_words = [
            "sad",
            "angry",
            "frustrated",
            "worried",
            "hate",
            "terrible",
            "awful",
        ]
        neutral_words = ["okay", "fine", "alright", "neutral", "normal"]

        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        neutral_count = sum(1 for word in neutral_words if word in text)

        if positive_count > negative_count and positive_count > neutral_count:
            return "positive"
        elif negative_count > positive_count and negative_count > neutral_count:
            return "negative"
        else:
            return "neutral"


def populate_initial_data():
    """Populate database with initial memory stream data"""
    try:
        # Sample initial memories for Charlotte
        initial_memories = [
            {
                "user_message": "Hello, I'm interested in your research on AI and consciousness.",
                "agent_response": "I'm excited to discuss my research! I've been exploring the intersection of artificial intelligence and consciousness, particularly focusing on how we can create systems that not only process information but also develop genuine understanding and awareness.",
                "conversation_topic": "academic_research",
                "emotional_context": "excited",
                "importance_score": 0.9,
                "is_active": True,
            },
            {
                "user_message": "What do you think about the future of AI?",
                "agent_response": "I believe the future of AI holds incredible potential, but also significant challenges. We need to ensure that AI development is guided by ethical principles and human values. My research focuses on creating AI systems that can collaborate meaningfully with humans while maintaining transparency and accountability.",
                "conversation_topic": "ai_future",
                "emotional_context": "thoughtful",
                "importance_score": 0.8,
                "is_active": True,
            },
            {
                "user_message": "How do you approach your research methodology?",
                "agent_response": "My research methodology combines theoretical analysis with practical experimentation. I start by reviewing existing literature, then develop hypotheses, design experiments, and analyze results. I believe in iterative refinement and always consider the broader implications of my work.",
                "conversation_topic": "research_methodology",
                "emotional_context": "focused",
                "importance_score": 0.7,
                "is_active": True,
            },
        ]

        # Insert initial memories
        for memory in initial_memories:
            supabase_extension.client.table("memory_stream").insert(memory).execute()

        print("Initial data populated successfully")

    except Exception as e:
        print(f"Error populating initial data: {e}")
        raise


def analyze_conversation_for_save(conversation_data: List[Dict]) -> Dict[str, Any]:
    """Analyze conversation and return metadata for saving"""
    try:
        # Extract text content
        text = " ".join([msg.get("text", "") for msg in conversation_data]).lower()

        # Generate title based on content
        title = _generate_title(conversation_data)

        # Generate description
        description = _generate_description(conversation_data)

        # Calculate quality score
        quality_score = _calculate_quality_score(conversation_data)

        # Analyze conversation type
        conversation_type = _classify_conversation_type(conversation_data)

        # Extract topics
        topics = _extract_conversation_topics(conversation_data)

        # Analyze emotional tone
        emotional_tone = _analyze_conversation_tone(conversation_data)

        # Assess conversation depth
        conversation_depth = _assess_conversation_depth(conversation_data)

        return {
            "title": title,
            "description": description,
            "quality_score": quality_score,
            "conversation_type": conversation_type,
            "topics": topics,
            "emotional_tone": emotional_tone,
            "conversation_depth": conversation_depth,
        }

    except Exception as e:
        print(f"Error analyzing conversation: {e}")
        return {
            "title": f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "description": "Conversation analysis failed",
            "quality_score": 0.5,
            "conversation_type": "unknown",
            "topics": ["general"],
            "emotional_tone": "neutral",
            "conversation_depth": "shallow",
        }


def populate_embeddings_for_existing_memories():
    """Populate embeddings for existing memories in the database"""
    try:
        print("\n=== POPULATING EMBEDDINGS FOR EXISTING MEMORIES ===")

        # Get all memories without embeddings from both tables
        memory_response = (
            supabase_extension.client.table("memory_stream")
            .select("*")
            .is_("embedding", "null")
            .execute()
        )

        conversations_response = (
            supabase_extension.client.table("saved_conversations")
            .select("*")
            .is_("embedding", "null")
            .execute()
        )

        updated_count = 0

        # Update memory_stream embeddings
        for memory in memory_response.data:
            try:
                # Generate embedding for the conversation context
                memory_text = f"{memory.get('user_message', '')} {memory.get('agent_response', '')}"
                embedding = generate_embedding(memory_text)

                # Update the memory with the embedding
                supabase_extension.client.table("memory_stream").update(
                    {"embedding": embedding}
                ).eq("id", memory["id"]).execute()

                updated_count += 1
                print(f"Updated memory {memory['id']} with embedding")
            except Exception as e:
                print(f"Error updating memory {memory['id']}: {e}")
                continue

        # Update saved_conversations embeddings
        for conv in conversations_response.data:
            try:
                # Generate embedding for the entire conversation
                conv_text = " ".join(
                    [
                        f"{msg.get('text', '')} {msg.get('user_message', '')} {msg.get('agent_response', '')}"
                        for msg in conv.get("conversation_data", [])
                    ]
                )
                embedding = generate_embedding(conv_text)

                # Update the conversation with the embedding
                supabase_extension.client.table("saved_conversations").update(
                    {"embedding": embedding}
                ).eq("id", conv["id"]).execute()

                updated_count += 1
                print(f"Updated conversation {conv['id']} with embedding")
            except Exception as e:
                print(f"Error updating conversation {conv['id']}: {e}")
                continue

        print(f"\nPopulated embeddings for {updated_count} items")

    except Exception as e:
        print(f"Error populating embeddings: {e}")
        raise


# Helper functions for conversation analysis
def _generate_title(conversation_data: List[Dict]) -> str:
    """Generate a title for the conversation"""
    if not conversation_data:
        return f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # Use the first user message as inspiration for title
    for msg in conversation_data:
        if msg.get("sender") == "user":
            text = msg.get("text", "")
            if len(text) > 10:
                # Take first few words and capitalize
                words = text.split()[:5]
                title = " ".join(words).capitalize()
                if len(title) > 50:
                    title = title[:47] + "..."
                return title

    return f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"


def _generate_description(conversation_data: List[Dict]) -> str:
    """Generate a description for the conversation"""
    if not conversation_data:
        return "No conversation content available"

    # Count messages by sender
    user_messages = [msg for msg in conversation_data if msg.get("sender") == "user"]
    bot_messages = [msg for msg in conversation_data if msg.get("sender") == "bot"]

    # Extract topics
    topics = _extract_conversation_topics(conversation_data)

    description = f"Conversation with {len(user_messages)} user messages and {len(bot_messages)} responses"
    if topics:
        description += f" about {', '.join(topics[:3])}"

    return description


def _calculate_quality_score(conversation_data: List[Dict]) -> float:
    """Calculate quality score for the conversation"""
    if not conversation_data:
        return 0.0

    score = 0.5  # Base score

    # Factors that increase score
    if len(conversation_data) >= 4:
        score += 0.2  # Longer conversations

    # Check for meaningful content
    total_length = sum(len(msg.get("text", "")) for msg in conversation_data)
    if total_length > 200:
        score += 0.1  # Substantial content

    # Check for balanced conversation
    user_messages = [msg for msg in conversation_data if msg.get("sender") == "user"]
    bot_messages = [msg for msg in conversation_data if msg.get("sender") == "bot"]
    if len(user_messages) > 0 and len(bot_messages) > 0:
        score += 0.1  # Balanced exchange

    # Check for specific topics (indicates focused conversation)
    topics = _extract_conversation_topics(conversation_data)
    if len(topics) > 1:
        score += 0.1  # Multiple topics discussed

    return min(1.0, score)


def _classify_conversation_type(conversation_data: List[Dict]) -> str:
    """Classify the type of conversation"""
    text = " ".join([msg.get("text", "") for msg in conversation_data]).lower()

    type_keywords = {
        "academic": [
            "research",
            "study",
            "paper",
            "analysis",
            "methodology",
            "academic",
        ],
        "technical": ["code", "programming", "algorithm", "system", "implementation"],
        "emotional": ["feel", "emotion", "sad", "happy", "excited", "worried"],
        "casual": ["hello", "how are you", "nice", "good", "thanks", "thank you"],
        "philosophical": [
            "think",
            "believe",
            "philosophy",
            "meaning",
            "purpose",
            "existence",
        ],
    }

    scores = {conv_type: 0 for conv_type in type_keywords.keys()}
    for conv_type, keywords in type_keywords.items():
        for keyword in keywords:
            if keyword in text:
                scores[conv_type] += 1

    # Return the type with highest score
    if scores:
        max_score = max(scores.values())
        for conv_type, score in scores.items():
            if score == max_score:
                return conv_type

    return "general"


def _extract_conversation_topics(conversation_data: List[Dict]) -> List[str]:
    """Extract topics from conversation"""
    text = " ".join([msg.get("text", "") for msg in conversation_data]).lower()

    topics = []
    topic_keywords = {
        "AI": ["ai", "artificial intelligence", "machine learning", "neural network"],
        "research": ["research", "study", "experiment", "analysis", "methodology"],
        "technology": ["technology", "tech", "software", "computer", "digital"],
        "philosophy": ["philosophy", "ethics", "morality", "meaning", "purpose"],
        "personal": ["personal", "life", "experience", "feelings", "emotions"],
        "academic": ["academic", "university", "education", "learning", "knowledge"],
    }

    for topic, keywords in topic_keywords.items():
        if any(keyword in text for keyword in keywords):
            topics.append(topic)

    return topics if topics else ["general"]


def _analyze_conversation_tone(conversation_data: List[Dict]) -> str:
    """Analyze the emotional tone of the conversation"""
    text = " ".join([msg.get("text", "") for msg in conversation_data]).lower()

    positive_words = [
        "happy",
        "excited",
        "great",
        "wonderful",
        "amazing",
        "love",
        "enjoy",
    ]
    negative_words = [
        "sad",
        "angry",
        "frustrated",
        "worried",
        "hate",
        "terrible",
        "awful",
        "bad",
    ]

    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)

    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    else:
        return "neutral"


def _assess_conversation_depth(conversation_data: List[Dict]) -> str:
    """Assess the depth of the conversation"""
    if not conversation_data:
        return "shallow"

    # Factors indicating depth
    total_length = sum(len(msg.get("text", "")) for msg in conversation_data)
    avg_length = total_length / len(conversation_data)

    # Check for complex topics
    topics = _extract_conversation_topics(conversation_data)
    has_complex_topics = any(
        topic in ["AI", "research", "philosophy", "academic"] for topic in topics
    )

    # Check for longer messages (indicating thoughtful responses)
    long_messages = sum(
        1 for msg in conversation_data if len(msg.get("text", "")) > 100
    )

    if (
        avg_length > 80
        and has_complex_topics
        and long_messages > len(conversation_data) / 2
    ):
        return "deep"
    elif avg_length > 50 or has_complex_topics:
        return "moderate"
    else:
        return "shallow"
