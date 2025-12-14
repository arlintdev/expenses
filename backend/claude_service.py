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

    def parse_expense_from_text(self, transcription: str, available_categories: list = None) -> Dict[str, Any]:
        """
        Parse expense information from transcribed text using Claude API.

        Args:
            transcription: The transcribed text to parse
            available_categories: List of user's existing categories for context
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # Build category context
        category_context = ""
        if available_categories and len(available_categories) > 0:
            category_list = ", ".join(available_categories)
            category_context = f"\n\nThe user has the following categories available: {category_list}\nIf the expense seems to fit one of these categories, use it. Otherwise, you can suggest a new category or leave it null."

        prompt = f"""You are an expense tracking assistant. Parse the following expense description and extract:
1. description: What the expense is for (title/description)
2. recipient: Who the expense is for
3. materials: Materials used (optional, only if mentioned - use null if not specified)
4. hours: The number of hours worked (optional, only if mentioned - use null if not specified)
5. category: The expense category (optional - use null if not specified){category_context}
6. amount: The numeric amount (just the number, no currency symbols) - REQUIRED
7. date: The date in YYYY-MM-DD format (if not mentioned, use today's date: {today})

Input: "{transcription}"

Respond ONLY with a JSON object in this exact format:
{{
    "description": "description here",
    "recipient": "recipient here",
    "materials": "materials_or_null",
    "hours": numeric_hours_or_null,
    "category": "category_or_null",
    "amount": numeric_amount,
    "date": "YYYY-MM-DD"
}}

If any information is missing or unclear, make reasonable assumptions based on context. The materials, hours, and category fields are optional - only include them if explicitly mentioned in the transcription."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text.strip()

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

            # Handle category (optional string field)
            if "category" not in parsed_data or parsed_data["category"] is None:
                parsed_data["category"] = None

            # Parse date string to datetime
            parsed_data["date"] = datetime.strptime(parsed_data["date"], "%Y-%m-%d")

            return parsed_data

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
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
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
            return transcription

        except Exception as e:
            raise ValueError(f"Error transcribing audio with Claude: {str(e)}")
