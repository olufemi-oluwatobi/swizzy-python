"""
Service for interacting with Google's Gemini API for multi-modal tasks.
"""
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
            logger.warning("GOOGLE_API_KEY environment variable not set. Gemini service will not function.")
        
        self.api_base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = "gemini-pro-vision"
    
    def _encode_image(self, image_bytes: bytes) -> str:
        """
        Encode image bytes to base64.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Base64 encoded image string
        """
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def analyze_image(self, image_bytes: bytes, prompt: str = "Extract all text from this image") -> Dict[str, Any]:
        """
        Analyze an image using Gemini Vision.
        
        Args:
            image_bytes: Raw image bytes
            prompt: Instruction for what to extract from the image
            
        Returns:
            Dictionary containing the analysis results
        """
        if not self.api_key:
            return {"error": "GOOGLE_API_KEY not set"}
        
        try:
            # Encode image to base64
            encoded_image = self._encode_image(image_bytes)
            
            # Prepare request payload
            url = f"{self.api_base_url}/models/{self.model}:generateContent?key={self.api_key}"
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",  # Adjust based on image type if needed
                                    "data": encoded_image
                                }
                            }
                        ]
                    }
                ]
            }
            
            # Make API request
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            # Extract text from response
            if "candidates" in result and result["candidates"]:
                content = result["candidates"][0].get("content", {})
                parts = content.get("parts", [])
                
                extracted_text = ""
                for part in parts:
                    if "text" in part:
                        extracted_text += part["text"]
                
                return {
                    "success": True,
                    "text": extracted_text,
                    "full_response": result
                }
            else:
                return {
                    "success": False,
                    "error": "No text found in the response",
                    "full_response": result
                }
                
        except Exception as e:
            logger.exception(f"Error analyzing image with Gemini: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def extract_structured_data(self, image_bytes: bytes, data_type: str = "invoice") -> Dict[str, Any]:
        """
        Extract structured data from an image.
        
        Args:
            image_bytes: Raw image bytes
            data_type: Type of data to extract (invoice, receipt, form, etc.)
            
        Returns:
            Dictionary containing the structured data
        """
        prompt = f"Extract all structured data from this {data_type} image. Format the output as JSON with appropriate fields."
        
        result = self.analyze_image(image_bytes, prompt)
        
        if result.get("success"):
            # Try to parse any JSON in the response text
            try:
                # Look for JSON-like content in the text
                text = result["text"]
                json_start = text.find('{')
                json_end = text.rfind('}')
                
                if json_start >= 0 and json_end > json_start:
                    json_str = text[json_start:json_end+1]
                    structured_data = json.loads(json_str)
                    result["structured_data"] = structured_data
                else:
                    # If no JSON found, keep the text as is
                    result["structured_data"] = {"raw_text": text}
            except json.JSONDecodeError:
                # If JSON parsing fails, keep the text as is
                result["structured_data"] = {"raw_text": result["text"]}
                
        return result
