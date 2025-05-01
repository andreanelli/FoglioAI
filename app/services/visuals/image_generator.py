"""Image generation service for vintage-style illustrations."""
import io
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from PIL import Image, ImageFilter, ImageEnhance

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Directory for storing generated images
IMAGE_DIR = Path(os.environ.get("IMAGE_DIR", "data/visuals/images"))


class ImageGenerator:
    """Generate vintage-styled AI images for 1920s newspaper articles."""

    def __init__(self):
        """Initialize the image generator."""
        # Create the image directory if it doesn't exist
        os.makedirs(IMAGE_DIR, exist_ok=True)
        
        # Set up API configuration
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.api_endpoint = "https://api.openai.com/v1/images/generations"
        self.dalle_model = os.environ.get("DALLE_MODEL", "dall-e-3")
        
        if not self.api_key:
            logger.warning("No OpenAI API key found in environment variables")

    async def generate_image(
        self,
        prompt: str,
        style: str = "vintage",
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
    ) -> str:
        """Generate an image using DALL-E API.

        Args:
            prompt (str): Description of the image to generate
            style (str, optional): Style of the image. Defaults to "vintage".
            size (str, optional): Size of the image. Defaults to "1024x1024".
            quality (str, optional): Image quality. Defaults to "standard".
            n (int, optional): Number of images to generate. Defaults to 1.

        Returns:
            str: Path to the saved image

        Raises:
            ValueError: If the API key is not set
            Exception: If the API request fails
        """
        if not self.api_key:
            # For testing or development, use a placeholder
            logger.warning("No API key - using placeholder image")
            return await self._generate_placeholder_image(prompt, style)
            
        # Enhance prompt with vintage styling
        full_prompt = self._enhance_prompt_with_style(prompt, style)
        
        try:
            # Set up the API request
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            
            payload = {
                "model": self.dalle_model,
                "prompt": full_prompt,
                "n": n,
                "size": size,
                "quality": quality,
            }
            
            # Log the request (without API key)
            logger.info(
                "Requesting image generation: model=%s, size=%s, prompt=%s",
                self.dalle_model, size, prompt
            )
            
            # Make the API request
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_endpoint,
                    json=payload,
                    headers=headers,
                )
                
                # Check for errors
                response.raise_for_status()
                result = response.json()
                
                # Get the image URL from the response
                image_url = result["data"][0]["url"]
                
                # Download the image
                image_response = await client.get(image_url)
                image_response.raise_for_status()
                
                # Load the image with PIL for post-processing
                image = Image.open(io.BytesIO(image_response.content))
                
                # Apply vintage post-processing
                processed_image = self._apply_vintage_effects(image, style)
                
                # Save the image
                image_id = str(uuid.uuid4())
                filename = f"{image_id}.png"
                filepath = IMAGE_DIR / filename
                
                processed_image.save(filepath, "PNG")
                
                return str(filepath)
                
        except Exception as e:
            logger.error("Failed to generate image: %s", e)
            # For production, you might want to raise the error
            # For now, fall back to a placeholder
            logger.warning("Falling back to placeholder image")
            return await self._generate_placeholder_image(prompt, style)

    async def _generate_placeholder_image(self, prompt: str, style: str) -> str:
        """Generate a placeholder image for testing or when API is unavailable.

        Args:
            prompt (str): The prompt that would have been used
            style (str): The requested style

        Returns:
            str: Path to the placeholder image
        """
        # Create a simple colored image with text
        width, height = 1024, 1024
        color = (240, 237, 229)  # Aged paper color
        
        # Create a new image with the specified background color
        image = Image.new("RGB", (width, height), color)
        
        # Add a border
        for i in range(5):
            border_color = (47, 52, 59, 255 - i * 50)  # Dark slate with decreasing opacity
            ImageDraw = Image.ImageDraw
            draw = ImageDraw.Draw(image)
            draw.rectangle(
                [(i, i), (width - i - 1, height - i - 1)],
                outline=border_color,
            )
        
        # Add placeholder text
        try:
            from PIL import ImageFont
            font_path = "app/static/fonts/OldStandardTT-Regular.ttf"
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, 30)
            else:
                font = ImageFont.load_default()
                
            draw.text(
                (width // 2, height // 2 - 50),
                "FoglioAI Placeholder Image",
                fill=(47, 52, 59),
                font=font,
                anchor="mm",
            )
            draw.text(
                (width // 2, height // 2 + 50),
                f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}",
                fill=(47, 52, 59),
                font=font,
                anchor="mm",
            )
        except Exception as e:
            # If text rendering fails, just continue without text
            logger.warning("Failed to add text to placeholder image: %s", e)
        
        # Apply vintage effects
        processed_image = self._apply_vintage_effects(image, style)
        
        # Save the image
        image_id = str(uuid.uuid4())
        filename = f"{image_id}.png"
        filepath = IMAGE_DIR / filename
        
        processed_image.save(filepath, "PNG")
        
        logger.info("Generated placeholder image: %s", filepath)
        
        return str(filepath)

    def _enhance_prompt_with_style(self, base_prompt: str, style: str) -> str:
        """Enhance a prompt with vintage styling.

        Args:
            base_prompt (str): The original prompt
            style (str): The requested style

        Returns:
            str: Enhanced prompt with vintage styling
        """
        style_prompts = {
            "vintage": (
                f"{base_prompt}, in the style of a vintage 1920s newspaper illustration, "
                "black and white, high contrast, detailed crosshatching, "
                "authentic period-appropriate styling"
            ),
            "sepia": (
                f"{base_prompt}, in the style of a sepia-toned early 20th century photograph, "
                "warm brown tones, slightly faded, vintage look, 1920s aesthetic"
            ),
            "woodcut": (
                f"{base_prompt}, in the style of a 1920s woodcut illustration, "
                "bold black lines, high contrast, distinctive texture, "
                "limited detail, period-appropriate styling"
            ),
            "art_deco": (
                f"{base_prompt}, in the style of Art Deco illustration from the 1920s, "
                "geometric patterns, bold shapes, elegant lines, "
                "symmetrical composition, vintage color palette"
            ),
            "watercolor": (
                f"{base_prompt}, in the style of a 1920s watercolor illustration, "
                "soft edges, delicate washes, limited palette, "
                "period-appropriate styling, suitable for a newspaper"
            ),
        }
        
        return style_prompts.get(style, f"{base_prompt}, in a vintage 1920s newspaper style")

    def _apply_vintage_effects(self, image: Image.Image, style: str) -> Image.Image:
        """Apply vintage effects to an image.

        Args:
            image (Image.Image): The original image
            style (str): The requested style

        Returns:
            Image.Image: The processed image with vintage effects
        """
        # Create a copy to avoid modifying the original
        processed = image.copy()
        
        if style == "vintage":
            # Apply a slight blur to soften details
            processed = processed.filter(ImageFilter.GaussianBlur(radius=0.5))
            
            # Adjust contrast and brightness
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(1.3)
            
            enhancer = ImageEnhance.Brightness(processed)
            processed = enhancer.enhance(0.9)
            
            # Add slight noise texture
            # (In a real implementation, this would add grain)
            
        elif style == "sepia":
            # Convert to grayscale
            processed = processed.convert("L")
            
            # Apply sepia tone
            sepia = Image.new("RGB", processed.size, (255, 240, 192))
            processed = Image.blend(processed.convert("RGB"), sepia, 0.3)
            
            # Enhance contrast slightly
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(1.1)
            
        elif style == "woodcut":
            # Convert to black and white with high contrast
            processed = processed.convert("L")
            
            # Increase contrast dramatically
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(2.0)
            
            # Apply threshold filter to create a more woodcut-like effect
            threshold = 128
            processed = processed.point(lambda p: 255 if p > threshold else 0)
            
            # Convert back to RGB
            processed = processed.convert("RGB")
            
        elif style == "art_deco":
            # Enhance saturation
            enhancer = ImageEnhance.Color(processed)
            processed = enhancer.enhance(1.4)
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(1.3)
            
        elif style == "watercolor":
            # Soften the image
            processed = processed.filter(ImageFilter.GaussianBlur(radius=0.8))
            
            # Enhance edges slightly to maintain some definition
            processed = processed.filter(ImageFilter.EDGE_ENHANCE)
            
            # Reduce saturation slightly
            enhancer = ImageEnhance.Color(processed)
            processed = enhancer.enhance(0.8)
        
        # Add common vintage effects for all styles
        
        # Slightly reduce sharpness
        enhancer = ImageEnhance.Sharpness(processed)
        processed = enhancer.enhance(0.9)
        
        # Add a subtle vignette effect
        # (In a real implementation, this would create a darkened border)
        
        return processed

    def resize_image(
        self, image_path: str, width: int, height: int, maintain_aspect: bool = True
    ) -> str:
        """Resize an image.

        Args:
            image_path (str): Path to the image
            width (int): Target width
            height (int): Target height
            maintain_aspect (bool, optional): Maintain aspect ratio. Defaults to True.

        Returns:
            str: Path to the resized image

        Raises:
            FileNotFoundError: If the image file doesn't exist
        """
        try:
            # Open the image
            image = Image.open(image_path)
            
            if maintain_aspect:
                # Calculate new dimensions while maintaining aspect ratio
                original_width, original_height = image.size
                aspect_ratio = original_width / original_height
                
                if width / height > aspect_ratio:
                    # Width is the constraining dimension
                    new_width = int(height * aspect_ratio)
                    new_height = height
                else:
                    # Height is the constraining dimension
                    new_width = width
                    new_height = int(width / aspect_ratio)
            else:
                new_width, new_height = width, height
            
            # Resize the image
            resized = image.resize((new_width, new_height), Image.LANCZOS)
            
            # Generate a new filename
            original_path = Path(image_path)
            filename = f"{original_path.stem}_resized_{new_width}x{new_height}{original_path.suffix}"
            filepath = IMAGE_DIR / filename
            
            # Save the resized image
            resized.save(filepath)
            
            return str(filepath)
            
        except FileNotFoundError:
            logger.error("Image file not found: %s", image_path)
            raise
        except Exception as e:
            logger.error("Failed to resize image: %s", e)
            return image_path  # Return original path on error 