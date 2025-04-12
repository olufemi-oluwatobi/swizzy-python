import os
import logging
import base64
from typing import Optional, List, Dict, Any, Union
import requests
import json

logger = logging.getLogger(__name__)

class GeminiService:
    """Service for interacting with Google's Gemini API."""

    def __init__(self):
        """Initialize the Gemini service."""
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            # Changed to error log level as this is critical
            logger.error("GOOGLE_API_KEY environment variable not set. Gemini service WILL NOT function.")
            # Optionally raise an exception if the key is absolutely required at init
            # raise ValueError("GOOGLE_API_KEY environment variable not set.")

        # Base URL remains the same
        self.api_base_url = "https://generativelanguage.googleapis.com/v1beta"
        # Default model for image analysis (can be overridden per method)
        self.vision_model = "gemini-2.0-flash"
        # Model suitable for PDF analysis (and other multi-modal tasks)
        self.multimodal_model = "gemini-2.0-flash" # Or "gemini-1.5-pro-latest" for more complex tasks

    def _encode_data(self, data_bytes: bytes) -> str:
        """
        Encode binary data (like images or PDFs) to base64.

        Args:
            data_bytes: Raw binary bytes

        Returns:
            Base64 encoded string
        """
        return base64.b64encode(data_bytes).decode('utf-8')

    def _make_request(self, model: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Helper function to make the API request to Gemini.

        Args:
            model: The specific Gemini model to use (e.g., "gemini-1.5-flash-latest").
            payload: The request payload dictionary.

        Returns:
            The parsed JSON response dictionary.

        Raises:
            requests.exceptions.RequestException: If the API request fails.
            ValueError: If API key is missing.
        """
        if not self.api_key:
           logger.error("Cannot make API request: GOOGLE_API_KEY not set.")
           # Returning an error structure consistent with other methods
           return {"success": False, "error": "GOOGLE_API_KEY not set"}

        url = f"{self.api_base_url}/models/{model}:generateContent?key={self.api_key}"
        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error making Gemini API request to {url}: {e}")
            # Propagate error details in the response
            error_detail = str(e)
            if e.response is not None:
                try:
                    error_detail += f" - Response: {e.response.text}"
                except Exception:
                    pass # Ignore if response text itself causes issues
            return {"success": False, "error": f"API request failed: {error_detail}"}
        except Exception as e: # Catch other potential errors during request/parsing
             logger.exception(f"Unexpected error during Gemini API request to {url}: {e}")
             return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def _parse_gemini_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the Gemini API response."""
        # Log the full response for debugging
        logger.info(f"Raw Gemini response: {json.dumps(result, indent=2)}")
        
        # Check if the result itself indicates a failure from _make_request
        if result.get("success") is False:
             return result # Pass through the pre-existing error

        try:
            if "candidates" in result and result["candidates"]:
                content = result["candidates"][0].get("content", {})
                parts = content.get("parts", [])

                extracted_text = "".join(part["text"] for part in parts if "text" in part)

                # Check if content was actually extracted
                if extracted_text:
                    return {
                        "success": True,
                        "text": extracted_text,
                        "full_response": result
                    }
                else:
                    # Check for safety ratings or blocks
                    finish_reason = result["candidates"][0].get("finishReason", "")
                    if finish_reason not in ["STOP", "MAX_TOKENS"]:
                         safety_ratings = result["candidates"][0].get("safetyRatings", [])
                         return {
                             "success": False,
                             "error": f"Content generation stopped due to: {finish_reason}. Safety Ratings: {safety_ratings}",
                             "full_response": result
                         }
                    else:
                        # Valid response, but no text parts found (unlikely but possible)
                         return {
                            "success": False,
                            "error": "API returned success, but no text content found in parts.",
                            "full_response": result
                         }
            # Handle promptFeedback block if content is missing/blocked
            elif "promptFeedback" in result:
                 block_reason = result["promptFeedback"].get("blockReason", "Unknown")
                 safety_ratings = result["promptFeedback"].get("safetyRatings", [])
                 return {
                     "success": False,
                     "error": f"Request blocked. Reason: {block_reason}. Safety Ratings: {safety_ratings}",
                     "full_response": result
                 }
            else:
                # General case if response structure is unexpected
                return {
                    "success": False,
                    "error": "Invalid response structure received from API. No candidates found.",
                    "full_response": result
                }
        except Exception as e:
            logger.exception(f"Error parsing Gemini response: {e}\nResponse: {result}")
            return {
                "success": False,
                "error": f"Failed to parse API response: {str(e)}",
                "full_response": result
            }


    def analyze_image(self, image_bytes: bytes, prompt: str = "Extract all text from this image", mime_type: str = "image/jpeg") -> Dict[str, Any]:
        """Analyze an image using Gemini Vision."""
        logger.info(f"Sending analysis request to Gemini. Prompt: {prompt}")
        
        if not self.api_key:
            return {"success": False, "error": "GOOGLE_API_KEY not set"}

        try:
            encoded_image = self._encode_data(image_bytes)

            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime_type, "data": encoded_image}}
                    ]
                }]
                # Add generationConfig here if needed (temperature, max tokens etc)
                # "generationConfig": {
                #     "temperature": 0.4,
                #     "topK": 32,
                #     "topP": 1.0,
                #     "maxOutputTokens": 4096,
                # }
            }

            # Use the dedicated vision model for this method
            result = self._make_request(self.vision_model, payload)
            
            # Log the parsed result
            logger.info(f"Parsed Gemini result: {json.dumps(result, indent=2)}")
            return self._parse_gemini_response(result)

        except Exception as e:
            logger.exception(f"Error preparing image analysis request: {e}")
            return {"success": False, "error": f"Failed to prepare request: {str(e)}"}

    # --- NEW METHOD ---
    def analyze_pdf(self, pdf_bytes: bytes, prompt: str = "Extract all text content from this PDF.") -> Dict[str, Any]:
        """
        Analyze a PDF document using Gemini.

        Args:
            pdf_bytes: Raw PDF file bytes.
            prompt: Instruction for what to extract or analyze from the PDF.
                    Examples:
                    - "Extract all text content from this PDF."
                    - "Summarize this document."
                    - "Extract the key points from this report."
                    - "What is the conclusion stated in this paper?"
                    - "Extract the table on page 5 as a markdown table."

        Returns:
            Dictionary containing the analysis results (extracted text, summary, etc.).
        """
        if not self.api_key:
            return {"success": False, "error": "GOOGLE_API_KEY not set"}

        try:
            # Encode PDF bytes to base64
            encoded_pdf = self._encode_data(pdf_bytes)

            # Prepare request payload for multi-modal model
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "application/pdf", # Specific MIME type for PDF
                                "data": encoded_pdf
                            }
                        }
                    ]
                }],
                 # Consider adding generationConfig if needed, especially maxOutputTokens for large PDFs
                 "generationConfig": {
                    # "temperature": 0.2, # Lower temp for more factual extraction
                    "maxOutputTokens": 8192, # Increase if expecting large text extraction
                 }
            }

            # Make API request using the multi-modal model
            # Using the model attribute defined in __init__
            result = self._make_request(self.multimodal_model, payload)

            # Parse the response using the common parsing logic
            return self._parse_gemini_response(result)

        except Exception as e:
            logger.exception(f"Error preparing PDF analysis request: {e}")
            return {"success": False, "error": f"Failed to prepare request: {str(e)}"}

    # --- analyze_structured_data method depends on analyze_image, ensure it uses appropriate mime_type ---
    def extract_structured_data(self, image_bytes: bytes, data_type: str = "invoice", mime_type: str = "image/jpeg") -> Dict[str, Any]:
        """
        Extract structured data from an image (e.g., invoice, receipt).

        Args:
            image_bytes: Raw image bytes.
            data_type: Type of data to extract (invoice, receipt, form, etc.), used in the prompt.
            mime_type: The MIME type of the image file.

        Returns:
            Dictionary containing the structured data, usually as JSON.
        """
        prompt = f"Analyze this image of a {data_type}. Extract all relevant structured data fields (like vendor name, total amount, date, line items, etc.). Format the output strictly as a single JSON object. Only output the JSON object."

        # Use analyze_image for the initial processing
        result = self.analyze_image(image_bytes, prompt, mime_type=mime_type)

        if result.get("success"):
            structured_data = {"raw_text": result["text"]} # Default fallback
            try:
                # Gemini is often good at returning JSON directly when asked.
                # Clean up potential markdown code fences if present
                text = result["text"].strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip() # Remove leading/trailing whitespace again

                # Attempt to parse the cleaned text as JSON
                parsed_json = json.loads(text)
                structured_data = parsed_json # Assign the parsed dict
                result["structured_data"] = structured_data
                # Remove raw text if JSON parsing succeeds to avoid redundancy? Optional.
                # result.pop("text", None)

            except json.JSONDecodeError as json_err:
                logger.warning(f"Failed to decode JSON from Gemini response for structured data extraction: {json_err}. Falling back to raw text.")
                # Keep the raw text in the structured_data field if JSON fails
                result["structured_data"] = {"raw_text": result["text"]}
                # We might add a flag indicating parsing failure
                result["json_parsing_failed"] = True
            except Exception as e:
                 logger.error(f"Unexpected error processing structured data response: {e}")
                 result["structured_data"] = {"raw_text": result["text"], "processing_error": str(e)}

        # Ensure structured_data key exists even if analyze_image failed initially
        elif "structured_data" not in result:
             result["structured_data"] = None

        return result

    def analyze_text(self, text: str, analysis_type: str = "General Analysis") -> Dict[str, Any]:
        """
        Analyze text content using Gemini's text model.

        Args:
            text: The text content to analyze
            analysis_type: Type of analysis to perform (used in logging)

        Returns:
            Dictionary containing the analysis results
        """
        logger.info(f"Sending {analysis_type} request to Gemini.")
        
        if not self.api_key:
            return {"success": False, "error": "GOOGLE_API_KEY not set"}

        try:
            # Prepare the payload for text analysis
            payload = {
                "contents": [{
                    "parts": [{"text": text}]
                }],
                "generationConfig": {
                    "temperature": 0.3,  # Lower temperature for more focused analysis
                    "maxOutputTokens": 8192,  # Allow for detailed analysis
                    "topP": 0.8,
                    "topK": 40
                }
            }

            # Use the multimodal model for text analysis
            result = self._make_request(self.multimodal_model, payload)
            return self._parse_gemini_response(result)

        except Exception as e:
            logger.exception(f"Error during text analysis: {e}")
            return {"success": False, "error": f"Failed to analyze text: {str(e)}"}
