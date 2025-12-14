import os
from anthropic import Anthropic
from datetime import datetime
import json
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

class ClaudeService:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        self.client = Anthropic(api_key=api_key)
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

    def parse_expense_from_text(self, transcription: str, available_tags: list = None, user_context: str = None) -> tuple[Dict[str, Any], Optional[str]]:
        """
        Parse expense information from transcribed text using Claude API.

        Args:
            transcription: The transcribed text to parse
            available_tags: List of user's existing tags for context
            user_context: Custom context provided by the user for expense generation

        Returns:
            Tuple of (parsed_data, warning_message)
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # Build tag context
        tag_context = ""
        if available_tags and len(available_tags) > 0:
            tag_list = ", ".join(available_tags)
            tag_context = f"\n\nThe user has the following tags available: {tag_list}\nIf the expense seems to fit one or more of these tags, use them. You can also suggest new tags or leave it empty."

        # Build user context
        context_instruction = ""
        if user_context and user_context.strip():
            context_instruction = f"\n\nIMPORTANT USER CONTEXT:\n{user_context}\n\nPlease follow these instructions when parsing and formatting the expense."

        prompt = f"""You are an expense tracking assistant. Parse the following expense description and extract:
1. description: What the expense is for (title/description)
2. recipient: Who the expense is for
3. materials: Materials used (optional, only if mentioned - use null if not specified)
4. hours: The number of hours worked (optional, only if mentioned - use null if not specified)
5. tags: An array of relevant tags/categories (optional - use empty array if not specified){tag_context}
6. amount: The numeric amount (just the number, no currency symbols) - REQUIRED
7. date: The date in YYYY-MM-DD format (if not mentioned, use today's date: {today}){context_instruction}

Input: "{transcription}"

Respond ONLY with a JSON object in this exact format:
{{
    "description": "description here",
    "recipient": "recipient here",
    "materials": "materials_or_null",
    "hours": numeric_hours_or_null,
    "tags": ["tag1", "tag2"],
    "amount": numeric_amount,
    "date": "YYYY-MM-DD"
}}

If any information is missing or unclear, make reasonable assumptions based on context. The materials, hours, and tags fields are optional - only include them if explicitly mentioned in the transcription. Tags should be an array of strings (e.g., ["food", "travel"])."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text.strip()

            # Check token usage
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens

            warning_message = None
            if input_tokens > 1000 or output_tokens > 1000:
                warning_message = f"Token limit exceeded: Input={input_tokens}/1000, Output={output_tokens}/1000"
                print(f"⚠️  {warning_message}")

            # Extract JSON from response (handle markdown code blocks)
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                json_lines = [line for line in lines if not line.startswith("```")]
                response_text = "\n".join(json_lines).strip()

            parsed_data = json.loads(response_text)

            # Validate required fields
            required_fields = ["description", "recipient", "amount", "date"]
            for field in required_fields:
                if field not in parsed_data:
                    raise ValueError(f"Missing required field: {field}")

            # Convert amount to float
            parsed_data["amount"] = float(parsed_data["amount"])

            # Handle materials (optional string field)
            if "materials" not in parsed_data or parsed_data["materials"] is None:
                parsed_data["materials"] = None

            # Convert hours to float if present and not null
            if "hours" in parsed_data and parsed_data["hours"] is not None:
                parsed_data["hours"] = float(parsed_data["hours"])
            else:
                parsed_data["hours"] = None

            # Handle tags (optional array field)
            if "tags" not in parsed_data or not isinstance(parsed_data["tags"], list):
                parsed_data["tags"] = []
            else:
                # Clean and deduplicate tags
                parsed_data["tags"] = [
                    tag.strip() for tag in parsed_data["tags"]
                    if tag and isinstance(tag, str) and tag.strip()
                ]
                parsed_data["tags"] = list(dict.fromkeys(parsed_data["tags"]))  # Remove duplicates

            # Parse date string to datetime
            parsed_data["date"] = datetime.strptime(parsed_data["date"], "%Y-%m-%d")

            return parsed_data, warning_message

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Claude response as JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error processing expense with Claude: {str(e)}")

    async def transcribe_audio(self, audio_base64: str, media_type: str) -> str:
        """
        Transcribe audio using Claude's audio understanding capability.

        Args:
            audio_base64: Base64 encoded audio data
            media_type: MIME type of the audio (e.g., 'audio/webm', 'audio/mp4')

        Returns:
            Transcribed text
        """
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": audio_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": "Please transcribe the audio. Only return the exact words spoken, nothing else."
                            }
                        ]
                    }
                ]
            )

            transcription = message.content[0].text.strip()

            # Check token usage
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens

            if input_tokens > 1000 or output_tokens > 1000:
                print(f"⚠️  Token limit warning (transcription): Input={input_tokens}/1000, Output={output_tokens}/1000")

            return transcription

        except Exception as e:
            raise ValueError(f"Error transcribing audio with Claude: {str(e)}")
