import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import requests
from io import BytesIO
from core.logger import log
from config import (
    TEMP_FOLDER, FONT_PATH_BOLD, FONT_PATH_REGULAR, 
    POSTER_TEMPLATE, CHANNEL_WATERMARK_HANDLE,
    TITLE_FONT_SIZE, RATING_FONT_SIZE, GENRE_FONT_SIZE, 
    YEAR_FONT_SIZE, WATERMARK_FONT_SIZE, POSTER_WIDTH, BLUR_RADIUS,
    CLEANUP_AFTER_SEND, TELEGRAM_LOGO_URL, TELEGRAM_LOGO_SIZE
)

class PosterGenerator:
    def __init__(self):
        self.font_bold = None
        self.font_regular = None
        self.template = None
        self.telegram_logo = None
        self.load_assets()
    
    def load_assets(self):
        """Load fonts, template and telegram logo with fallbacks"""
        try:
            # Load fonts with fallbacks
            try:
                if os.path.exists(FONT_PATH_BOLD):
                    self.font_bold = ImageFont.truetype(FONT_PATH_BOLD, TITLE_FONT_SIZE)
                    log.success("✅ Bold font loaded successfully")
                else:
                    self.font_bold = ImageFont.load_default()
                    log.info("📝 Using system fallback for bold font")
                
                if os.path.exists(FONT_PATH_REGULAR):
                    self.font_regular = ImageFont.truetype(FONT_PATH_REGULAR, RATING_FONT_SIZE)
                    log.success("✅ Regular font loaded successfully")
                else:
                    self.font_regular = ImageFont.load_default()
                    log.info("📝 Using system fallback for regular font")
                    
            except Exception as e:
                log.warning(f"⚠️ Could not load custom fonts: {e}")
                self.font_bold = ImageFont.load_default()
                self.font_regular = ImageFont.load_default()
            
            # Load template
            try:
                if os.path.exists(POSTER_TEMPLATE):
                    self.template = Image.open(POSTER_TEMPLATE).convert("RGB")
                    log.success("✅ Poster template loaded successfully")
                else:
                    self.template = None
                    log.info("🎨 No template found - will use blur background")
                    
            except Exception as e:
                log.error(f"💥 Error loading template: {e}")
                self.template = None
            
            # Load Telegram logo
            try:
                if TELEGRAM_LOGO_URL:
                    response = requests.get(TELEGRAM_LOGO_URL, timeout=10)
                    response.raise_for_status()
                    self.telegram_logo = Image.open(BytesIO(response.content)).convert("RGBA")
                    # Resize logo
                    self.telegram_logo = self.telegram_logo.resize((TELEGRAM_LOGO_SIZE, TELEGRAM_LOGO_SIZE), Image.LANCZOS)
                    log.success("✅ Telegram logo loaded successfully")
                else:
                    self.telegram_logo = None
                    log.info("📱 No Telegram logo URL provided")
            except Exception as e:
                log.warning(f"⚠️ Could not load Telegram logo: {e}")
                self.telegram_logo = None
                
        except Exception as e:
            log.error(f"💥 Error loading assets: {e}")
    
    def create_blur_background(self, poster_image: Image.Image, width=1280, height=720) -> Image.Image:
        """Create a beautiful blur background from the poster image"""
        try:
            # Resize poster to cover entire canvas while maintaining aspect ratio
            poster_ratio = poster_image.width / poster_image.height
            canvas_ratio = width / height
            
            if poster_ratio > canvas_ratio:
                # Poster is wider than canvas
                new_height = height
                new_width = int(poster_image.width * (height / poster_image.height))
            else:
                # Poster is taller than canvas
                new_width = width
                new_height = int(poster_image.height * (width / poster_image.width))
            
            # Resize poster to cover canvas
            resized_poster = poster_image.resize((new_width, new_height), Image.LANCZOS)
            
            # Crop to canvas size (center crop)
            left = (new_width - width) // 2
            top = (new_height - height) // 2
            right = left + width
            bottom = top + height
            cropped_poster = resized_poster.crop((left, top, right, bottom))
            
            # Apply blur effect
            blurred_background = cropped_poster.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))
            
            # Add dark overlay for better text readability
            overlay = Image.new('RGBA', (width, height), (0, 0, 0, 180))
            background = Image.alpha_composite(blurred_background.convert('RGBA'), overlay)
            
            log.debug("✅ Blur background created successfully")
            return background.convert('RGB')
            
        except Exception as e:
            log.error(f"💥 Error creating blur background: {e}")
            return self.create_gradient_background(width, height)
    
    def create_gradient_background(self, width=1280, height=720):
        """Create a beautiful gradient background as fallback"""
        try:
            # Create a base image with dark background
            base = Image.new('RGB', (width, height), color=(20, 25, 35))
            
            # Create gradient overlay
            gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(gradient)
            
            # Draw gradient from top to bottom (dark blue to purple)
            for y in range(height):
                r = int(20 + (y / height) * 30)
                g = int(25 + (y / height) * 15)
                b = int(35 + (y / height) * 40)
                alpha = int(180 * (y / height))
                draw.line([(0, y), (width, y)], fill=(r, g, b, alpha))
            
            # Composite the gradient over base
            background = Image.alpha_composite(base.convert('RGBA'), gradient)
            return background.convert('RGB')
            
        except Exception as e:
            log.error(f"💥 Error creating gradient: {e}")
            return Image.new('RGB', (width, height), color=(25, 30, 40))
    
    def download_poster_image(self, poster_url: str) -> Image.Image:
        """Download and process poster image from TMDB"""
        try:
            if not poster_url:
                raise ValueError("No poster URL provided")
            
            log.debug(f"📥 Downloading poster from: {poster_url}")
            response = requests.get(poster_url, timeout=20)
            response.raise_for_status()
            
            # Open image from bytes
            poster_image = Image.open(BytesIO(response.content)).convert("RGB")
            log.success("✅ Poster image downloaded successfully")
            return poster_image
            
        except Exception as e:
            log.error(f"💥 Error downloading poster: {e}")
            # Return a placeholder image
            return self._create_placeholder_poster()
    
    def _create_placeholder_poster(self) -> Image.Image:
        """Create a placeholder when no poster is available"""
        placeholder = Image.new('RGB', (400, 600), color=(40, 45, 60))
        draw = ImageDraw.Draw(placeholder)
        
        # Add text to placeholder
        try:
            font = ImageFont.truetype(FONT_PATH_BOLD, 48) if os.path.exists(FONT_PATH_BOLD) else ImageFont.load_default()
            draw.text((200, 300), "NO POSTER", fill=(200, 200, 200), anchor="mm", font=font)
        except:
            draw.text((200, 300), "NO POSTER", fill=(200, 200, 200), anchor="mm")
        
        return placeholder
    
    def generate_poster(self, movie_data: dict, output_path: str = None) -> str:
        """Generate the final movie poster with blur background"""
        try:
            log.info(f"🎨 Generating poster for: {movie_data['title']}")
            
            # Download movie poster first
            poster_image = self.download_poster_image(movie_data.get('poster_url', ''))
            
            # Create canvas with blur background
            width, height = 1280, 720
            if self.template:
                canvas = self.template.copy().resize((width, height))
            else:
                canvas = self.create_blur_background(poster_image, width, height)
            
            draw = ImageDraw.Draw(canvas)
            
            # Resize poster to fit right side (maintain aspect ratio)
            poster_height = int(height * 0.75)  # 75% of canvas height
            poster_width = int(poster_image.width * (poster_height / poster_image.height))
            
            # Ensure poster doesn't get too wide
            if poster_width > POSTER_WIDTH:
                poster_width = POSTER_WIDTH
                poster_height = int(poster_image.height * (POSTER_WIDTH / poster_image.width))
            
            poster_image = poster_image.resize((poster_width, poster_height), Image.LANCZOS)
            
            # Position poster on right side with margin
            poster_x = width - poster_width - 60
            poster_y = (height - poster_height) // 2
            
            # Create poster frame with shadow effect
            self._draw_poster_with_frame(canvas, poster_image, poster_x, poster_y)
            
            # Add movie information on left side
            self._draw_movie_info(draw, movie_data, poster_x)
            
            # Add watermark with Telegram logo
            self._draw_watermark_with_logo(canvas, draw, width, height)
            
            # Save the final image
            if not output_path:
                os.makedirs(TEMP_FOLDER, exist_ok=True)
                output_path = os.path.join(TEMP_FOLDER, f"{movie_data['movie_id']}_{movie_data['title'].replace(' ', '_')}.jpg")
            
            canvas.save(output_path, "JPEG", quality=95)
            log.success(f"✅ Poster generated successfully: {output_path}")
            
            return output_path
            
        except Exception as e:
            log.error(f"💥 Error generating poster: {e}")
            raise
    
    def cleanup_poster(self, poster_path: str):
        """Clean up generated poster file"""
        try:
            if CLEANUP_AFTER_SEND and os.path.exists(poster_path):
                os.remove(poster_path)
                log.debug(f"🧹 Cleaned up poster file: {poster_path}")
        except Exception as e:
            log.warning(f"⚠️ Could not clean up poster file {poster_path}: {e}")
    
    def _draw_poster_with_frame(self, canvas: Image.Image, poster: Image.Image, x: int, y: int):
        """Draw poster with a nice frame and shadow"""
        try:
            # Add subtle shadow
            shadow_offset = 8
            shadow = Image.new('RGBA', (poster.width + shadow_offset, poster.height + shadow_offset), (0, 0, 0, 120))
            canvas.paste(shadow, (x + shadow_offset, y + shadow_offset), shadow)
            
            # Add glossy frame
            frame_size = 6
            frame = Image.new('RGBA', (poster.width + frame_size*2, poster.height + frame_size*2), (255, 255, 255, 80))
            canvas.paste(frame, (x - frame_size, y - frame_size), frame)
            
            # Paste the actual poster
            canvas.paste(poster, (x, y))
            
            # Add inner border
            draw = ImageDraw.Draw(canvas)
            draw.rectangle([
                x - 2, y - 2,
                x + poster.width + 2, y + poster.height + 2
            ], outline=(255, 255, 255, 200), width=2)
            
        except Exception as e:
            log.error(f"💥 Error drawing poster frame: {e}")
            # Fallback: just paste the poster
            canvas.paste(poster, (x, y))
    
    def _draw_movie_info(self, draw: ImageDraw.Draw, movie_data: dict, poster_start_x: int):
        """Draw movie information on the left side with new format"""
        try:
            margin_left = 60
            current_y = 80
            line_spacing = 15
            
            # Movie Title (big and bold as main title)
            title = movie_data['title']
            
            # Adjust font size for long titles
            title_font_size = TITLE_FONT_SIZE
            if len(title) > 25:
                title_font_size = int(TITLE_FONT_SIZE * 0.8)
            if len(title) > 35:
                title_font_size = int(TITLE_FONT_SIZE * 0.65)
            
            try:
                title_font = ImageFont.truetype(FONT_PATH_BOLD, title_font_size) if os.path.exists(FONT_PATH_BOLD) else ImageFont.load_default()
            except:
                title_font = ImageFont.load_default()
            
            # Wrap long titles
            words = title.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                # Use textsize for older PIL versions
                try:
                    text_width = draw.textlength(test_line, font=title_font)
                except:
                    bbox = draw.textbbox((0, 0), test_line, font=title_font)
                    text_width = bbox[2] - bbox[0]
                
                if text_width < (poster_start_x - margin_left - 40):
                    current_line.append(word)
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Draw title lines with shadow effect
            for i, line in enumerate(lines):
                # Shadow
                draw.text((margin_left + 2, current_y + 2), line, fill=(0, 0, 0, 150), font=title_font)
                # Main text
                draw.text((margin_left, current_y), line, fill=(255, 255, 255), font=title_font)
                current_y += title_font_size + line_spacing
            
            current_y += 40
            
            # Genres with hashtags (using ✲ emoji)
            genres = movie_data.get('genres', [])
            if genres:
                genre_hashtags = " ".join([f"#{genre.replace(' ', '')}" for genre in genres[:3]])
                genres_text = f"✲ Genre: {genre_hashtags}"
                try:
                    genre_font = ImageFont.truetype(FONT_PATH_REGULAR, GENRE_FONT_SIZE) if os.path.exists(FONT_PATH_REGULAR) else ImageFont.load_default()
                except:
                    genre_font = ImageFont.load_default()
                
                # Shadow
                draw.text((margin_left + 2, current_y + 2), genres_text, fill=(0, 0, 0, 150), font=genre_font)
                # Main text (light purple)
                draw.text((margin_left, current_y), genres_text, fill=(200, 180, 255), font=genre_font)
                current_y += GENRE_FONT_SIZE + 25
            
            # TMDB Rating (using ≛ emoji)
            rating = movie_data.get('tmdb_rating', 0)
            if rating > 0:
                rating_text = f"≛ IMDb : {rating} / 10"
                try:
                    rating_font = ImageFont.truetype(FONT_PATH_REGULAR, RATING_FONT_SIZE) if os.path.exists(FONT_PATH_REGULAR) else ImageFont.load_default()
                except:
                    rating_font = ImageFont.load_default()
                
                # Shadow
                draw.text((margin_left + 2, current_y + 2), rating_text, fill=(0, 0, 0, 150), font=rating_font)
                # Main text (gold color)
                draw.text((margin_left, current_y), rating_text, fill=(255, 215, 0), font=rating_font)
                current_y += RATING_FONT_SIZE + 25
            
            # Language (using ✢ emoji)
            original_language = movie_data.get('original_language', 'en')
            language_map = {
                'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
                'it': 'Italian', 'ja': 'Japanese', 'ko': 'Korean', 'zh': 'Chinese',
                'hi': 'Hindi', 'ar': 'Arabic', 'ru': 'Russian', 'pt': 'Portuguese'
            }
            language_name = language_map.get(original_language, 'English')
            language_text = f"✢ Language :  #{language_name}"
            try:
                language_font = ImageFont.truetype(FONT_PATH_REGULAR, YEAR_FONT_SIZE) if os.path.exists(FONT_PATH_REGULAR) else ImageFont.load_default()
            except:
                language_font = ImageFont.load_default()
            
            # Shadow
            draw.text((margin_left + 2, current_y + 2), language_text, fill=(0, 0, 0, 150), font=language_font)
            # Main text (light blue)
            draw.text((margin_left, current_y), language_text, fill=(180, 220, 255), font=language_font)
                
        except Exception as e:
            log.error(f"💥 Error drawing movie info: {e}")
    
    def _draw_watermark_with_logo(self, canvas: Image.Image, draw: ImageDraw.Draw, width: int, height: int):
        """Add watermark with Telegram logo to the poster with fallback"""
        try:
            watermark = CHANNEL_WATERMARK_HANDLE
            try:
                watermark_font = ImageFont.truetype(FONT_PATH_REGULAR, WATERMARK_FONT_SIZE) if os.path.exists(FONT_PATH_REGULAR) else ImageFont.load_default()
            except:
                watermark_font = ImageFont.load_default()
            
            # Calculate text position using compatible method
            try:
                # For newer PIL versions
                bbox = draw.textbbox((0, 0), watermark, font=watermark_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            except:
                # For older PIL versions
                try:
                    text_width = draw.textlength(watermark, font=watermark_font)
                    text_height = WATERMARK_FONT_SIZE
                except:
                    # Fallback
                    text_width = len(watermark) * (WATERMARK_FONT_SIZE // 2)
                    text_height = WATERMARK_FONT_SIZE
            
            # Position at bottom left
            logo_spacing = 10
            total_width = TELEGRAM_LOGO_SIZE + logo_spacing + text_width
            start_x = 20
            start_y = height - 40 - (TELEGRAM_LOGO_SIZE // 2)
            
            # Draw Telegram logo if available
            if self.telegram_logo:
                try:
                    canvas.paste(self.telegram_logo, (start_x, start_y), self.telegram_logo)
                    text_x = start_x + TELEGRAM_LOGO_SIZE + logo_spacing
                except Exception as e:
                    log.warning(f"⚠️ Could not paste Telegram logo: {e}")
                    text_x = start_x
            else:
                text_x = start_x
            
            # Shadow for text
            draw.text(
                (text_x + 2, start_y + 2 - (text_height // 2)), 
                watermark, 
                fill=(0, 0, 0, 150), 
                font=watermark_font
            )
            
            # Main text
            draw.text(
                (text_x, start_y - (text_height // 2)), 
                watermark, 
                fill=(180, 180, 180, 220), 
                font=watermark_font
            )
            
            log.debug("✅ Watermark added successfully")
            
        except Exception as e:
            log.error(f"💥 Error drawing watermark with logo: {e}")
            # Fallback: simple watermark without logo
            try:
                draw.text(
                    (20, height - 40), 
                    watermark, 
                    fill=(180, 180, 180, 220), 
                    font=watermark_font
                )
                log.info("✅ Fallback watermark added")
            except:
                log.error("💥 Could not add fallback watermark")

# Global poster generator instance
poster_generator = PosterGenerator()