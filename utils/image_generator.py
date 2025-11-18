import os
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import requests
from io import BytesIO
from core.logger import log
from config import (
    TEMP_FOLDER, FONT_PATH_BOLD, FONT_PATH_REGULAR,
    CHANNEL_WATERMARK_HANDLE, TELEGRAM_LOGO_URL, TELEGRAM_LOGO_SIZE,
    POSTER_WIDTH, POSTER_HEIGHT, POSTER_CORNER_RADIUS, POSTER_SHADOW_BLUR, POSTER_SHADOW_OFFSET,
    COLOR_TEXT_LIGHT, COLOR_TEXT_SUBTLE, COLOR_SHADOW, COLOR_RATING_BADGE, COLOR_RATING_TEXT,
    COLOR_GLASS_TINT, GLASS_OPACITY, GLASS_BLUR_RADIUS,
    TITLE_FONT_SIZE, GENRE_FONT_SIZE, RATING_FONT_SIZE, STORYLINE_FONT_SIZE, WATERMARK_FONT_SIZE,
    CLEANUP_AFTER_SEND, COLOR_TEXT_GENRE
)

class PosterGenerator:
    def __init__(self):
        self.font_bold = None
        self.font_regular = None
        self.telegram_logo = None
        self.load_assets()
    
    def load_assets(self):
        """Load fonts and Telegram logo with fallbacks"""
        try:
            # Load fonts
            try:
                if os.path.exists(FONT_PATH_BOLD):
                    self.font_bold = ImageFont.truetype(FONT_PATH_BOLD, TITLE_FONT_SIZE)
                    log.success("✅ Bold font loaded successfully")
                else:
                    self.font_bold = ImageFont.load_default()
                    log.info("📝 Using system fallback for bold font")
                
                if os.path.exists(FONT_PATH_REGULAR):
                    self.font_regular = ImageFont.truetype(FONT_PATH_REGULAR, GENRE_FONT_SIZE)
                    log.success("✅ Regular font loaded successfully")
                else:
                    self.font_regular = ImageFont.load_default()
                    log.info("📝 Using system fallback for regular font")
                    
            except Exception as e:
                log.warning(f"⚠️ Could not load custom fonts: {e}")
                self.font_bold = ImageFont.load_default()
                self.font_regular = ImageFont.load_default()
            
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
    
    def download_image(self, url, is_logo=False):
        """Download image from URL and return PIL Image object"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert("RGBA")
        except Exception as e:
            log.error(f"Error downloading image: {e}")
            if not is_logo:
                return Image.new('RGBA', (300, 450), color='#1a1a1a')
            return None
    
    def apply_background_blur(self, poster_img, blur_radius=20):
        """Apply blur effect to background"""
        try:
            bg = poster_img.resize((POSTER_WIDTH, POSTER_HEIGHT), Image.LANCZOS)
        except Exception:
            bg = poster_img.convert("RGB").resize((POSTER_WIDTH, POSTER_HEIGHT), Image.LANCZOS)

        bg = bg.filter(ImageFilter.GaussianBlur(blur_radius))
        enhancer = ImageEnhance.Brightness(bg)
        bg = enhancer.enhance(0.6)  # Darken a bit more
        return bg.convert("RGBA")
    
    def create_glass_effect(self, base_image, position, radius, color, opacity=60, blur=4):
        """
        Applies a true "frosted glass" effect by blurring the background
        behind the panel.
        """
        x1, y1, x2, y2 = position

        # 1. Crop the area from the base image
        crop = base_image.crop(position)

        # 2. Apply a light "frost" blur to this crop
        blurred_crop = crop.filter(ImageFilter.GaussianBlur(blur))

        # 3. Paste the frosted crop back onto the base image
        base_image.paste(blurred_crop, (x1, y1))

        # 4. Create a new layer for the semi-transparent tint/border
        glass_layer = Image.new('RGBA', base_image.size, (0, 0, 0, 0))
        draw_glass = ImageDraw.Draw(glass_layer)

        # 5. Draw the tint
        draw_glass.rounded_rectangle(position, radius=radius, fill=color + (opacity,))

        # 6. (Optional) Add a subtle 1px border
        draw_glass.rounded_rectangle(position, radius=radius, outline=(255, 255, 255, 80), width=1)

        # 7. Composite the tint layer onto the base image
        return Image.alpha_composite(base_image, glass_layer)
    
    def add_rounded_corners(self, im, radius):
        """Applies rounded corners to an image."""
        circle = Image.new('L', (radius * 2, radius * 2), 0)
        draw = ImageDraw.Draw(circle)
        draw.ellipse((0, 0, radius * 2, radius * 2), fill=255)

        alpha = Image.new('L', im.size, 255)
        w, h = im.size

        alpha.paste(circle.crop((0, 0, radius, radius)), (0, 0))
        alpha.paste(circle.crop((0, radius, radius, radius * 2)), (0, h - radius))
        alpha.paste(circle.crop((radius, 0, radius * 2, radius)), (w - radius, 0))
        alpha.paste(circle.crop((radius, radius, radius * 2, radius * 2)), (w - radius, h - radius))

        im.putalpha(alpha)
        return im
    
    def create_soft_shadow(self, image, blur, offset, color):
        """Creates a soft, offset Gaussian shadow image for another image."""
        w, h = image.size
        padding_x = blur + abs(offset[0])
        padding_y = blur + abs(offset[1])

        shadow_w = w + padding_x * 2
        shadow_h = h + padding_y * 2

        shadow_canvas = Image.new('RGBA', (shadow_w, shadow_h), (0, 0, 0, 0))

        paste_x_on_shadow = padding_x - offset[0]
        paste_y_on_shadow = padding_y - offset[1]

        shadow_draw = ImageDraw.Draw(shadow_canvas)
        shadow_draw.rounded_rectangle(
            (paste_x_on_shadow, paste_y_on_shadow, paste_x_on_shadow + w, paste_y_on_shadow + h),
            radius=POSTER_CORNER_RADIUS,
            fill=color
        )

        return shadow_canvas.filter(ImageFilter.GaussianBlur(blur))
    
    def draw_text_with_shadow(self, draw, position, text, font, fill=COLOR_TEXT_LIGHT, shadow_color=COLOR_SHADOW):
        """Draws text with a simple, clean drop shadow."""
        x, y = position
        # Draw shadow
        draw.text((x + 2, y + 2), text, font=font, fill=shadow_color)
        # Draw main text
        draw.text((x, y), text, font=font, fill=fill)
    
    def draw_badge(self, draw, x, y, text, font, bg_color, text_color):
        """Draws a rounded "pill" badge and returns its width."""
        padding_x = 18
        padding_y = 10

        try:
            text_w = draw.textlength(text, font=font)
            bbox = font.getbbox("A")
            text_h = bbox[3] - bbox[1]
            text_y_offset = bbox[1]
        except AttributeError:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            text_y_offset = bbox[1]

        box_w = text_w + (padding_x * 2)
        box_h = text_h + (padding_y * 2)

        draw.rounded_rectangle(
            (x, y, x + box_w, y + box_h),
            radius=int(box_h / 2),
            fill=bg_color
        )

        text_x = x + padding_x
        text_y = y + (box_h - text_h) // 2 - text_y_offset
        draw.text((text_x, text_y), text, fill=text_color, font=font)

        return box_w + 15
    
    def generate_poster(self, movie_data: dict, output_path: str = None) -> str:
        """Generate the final movie poster with glass theme and storyline"""
        try:
            # Ensure required fields exist with fallbacks
            movie_data.setdefault('language', movie_data.get('original_language', 'EN'))
            movie_data.setdefault('tmdb_rating', 0)
            movie_data.setdefault('genres', [])
            movie_data.setdefault('storyline', movie_data.get('overview', ''))
            movie_data.setdefault('overview', '')
            
            log.info(f"🎨 Generating glass-themed poster for: {movie_data['title']}")
            
            # 1. Download and prepare background
            try:
                poster_img = self.download_image(movie_data["poster_url"])
                base_image = self.apply_background_blur(poster_img)
            except Exception as e:
                log.error(f"Error creating background: {e}")
                base_image = Image.new('RGBA', (POSTER_WIDTH, POSTER_HEIGHT), color='#0f1419')

            # 2. Prepare "Floating" Poster (Left side)
            try:
                poster_display = poster_img.resize((350, 525), Image.LANCZOS)
                poster_display = self.add_rounded_corners(poster_display, POSTER_CORNER_RADIUS)

                # Create shadow for poster
                shadow = self.create_soft_shadow(
                    poster_display,
                    blur=POSTER_SHADOW_BLUR,
                    offset=POSTER_SHADOW_OFFSET,
                    color=COLOR_SHADOW
                )

                # Paste shadow and poster
                poster_x = 75
                poster_y = (POSTER_HEIGHT - 525) // 2

                shadow_x = poster_x - (POSTER_SHADOW_BLUR + POSTER_SHADOW_OFFSET[0])
                shadow_y = poster_y - (POSTER_SHADOW_BLUR + POSTER_SHADOW_OFFSET[1])

                base_image.paste(shadow, (shadow_x, shadow_y), shadow)
                base_image.paste(poster_display, (poster_x, poster_y), poster_display)

            except Exception as e:
                log.error(f"Error processing poster: {e}")

            # 3. Create "Frosted Glass" Info Panel (Right side)
            glass_pos = (480, 75, POSTER_WIDTH - 75, POSTER_HEIGHT - 75)
            base_image = self.create_glass_effect(
                base_image, glass_pos, 20, COLOR_GLASS_TINT, GLASS_OPACITY, GLASS_BLUR_RADIUS
            )

            # Re-initialize Draw object after all background modifications
            draw = ImageDraw.Draw(base_image)

            # 4. Add Text Content
            text_start_x = 515
            text_start_y = 110
            current_y = text_start_y

            # Movie title with automatic size adjustment
            title = movie_data["title"].upper()

            # Calculate title length and adjust font size
            title_length = len(title)
            if title_length > 40:
                # Very long title - use smaller font
                title_font_size = int(TITLE_FONT_SIZE * 0.7)
            elif title_length > 25:
                # Long title - use medium font
                title_font_size = int(TITLE_FONT_SIZE * 0.8)
            else:
                # Normal title - use regular font
                title_font_size = TITLE_FONT_SIZE

            # Load the appropriate font
            try:
                title_font = ImageFont.truetype(FONT_PATH_BOLD, title_font_size) if os.path.exists(FONT_PATH_BOLD) else ImageFont.load_default()
            except:
                title_font = self.font_bold

            # Adjust wrap width based on font size
            wrap_width = 35 if title_font_size < TITLE_FONT_SIZE else 30
            title_lines = textwrap.wrap(title, width=wrap_width)

            # Adjust line height based on font size
            line_height = int(title_font_size * 1.3)

            # Draw title lines
            for line in title_lines:
                self.draw_text_with_shadow(draw, (text_start_x, current_y), line, title_font)
                current_y += line_height

            current_y += 20  # Reduced space after title


            current_y += 30

            # Genres with automatic size adjustment
            genres_text = " • ".join(movie_data["genres"]).upper()

            # Calculate genres length and adjust font size
            genres_length = len(genres_text)
            if genres_length > 50:
                # Very long genres - use smaller font
                genre_font_size = int(GENRE_FONT_SIZE * 0.7)
            elif genres_length > 35:
                # Long genres - use medium font
                genre_font_size = int(GENRE_FONT_SIZE * 0.8)
            else:
                # Normal genres - use regular font
                genre_font_size = GENRE_FONT_SIZE

            # Load the appropriate font
            try:
                genre_font = ImageFont.truetype(FONT_PATH_REGULAR, genre_font_size) if os.path.exists(FONT_PATH_REGULAR) else ImageFont.load_default()
            except:
                genre_font = self.font_regular

            # Draw genres text
            self.draw_text_with_shadow(draw, (text_start_x, current_y), genres_text, genre_font, fill=COLOR_TEXT_GENRE)

            # Adjust spacing based on font size
            current_y += int(genre_font_size * 2)  # Dynamic spacing after genres

            # Rating & Language Badges
            current_x = text_start_x

            try:
                badge_font = ImageFont.truetype(FONT_PATH_BOLD, RATING_FONT_SIZE) if os.path.exists(FONT_PATH_BOLD) else ImageFont.load_default()
            except:
                badge_font = ImageFont.load_default()

            # Rating Badge - WITH FALLBACK
            rating_value = movie_data.get('tmdb_rating', 0)
            rating_text = f"⭐ {rating_value}/10" if rating_value > 0 else "⭐ N/A"
            width = self.draw_badge(draw, current_x, current_y, rating_text, badge_font, COLOR_RATING_BADGE, COLOR_RATING_TEXT)
            current_x += width

            # Language Badge - WITH FALLBACK
            lang_text = movie_data.get('language', 'EN').upper()
            self.draw_badge(draw, current_x, current_y, lang_text, badge_font, (33, 150, 243), COLOR_TEXT_LIGHT)

            current_y += 80

            # Storyline
            storyline = movie_data.get('storyline', movie_data.get('overview', ''))
            if storyline:
                try:
                    storyline_font = ImageFont.truetype(FONT_PATH_REGULAR, STORYLINE_FONT_SIZE) if os.path.exists(FONT_PATH_REGULAR) else ImageFont.load_default()
                except:
                    storyline_font = ImageFont.load_default()
                
                max_width = (POSTER_WIDTH - 75) - text_start_x - 20
                storyline_lines = textwrap.wrap(storyline, width=50)
                storyline_lines = storyline_lines[:5]

                for line in storyline_lines:
                    if current_y < POSTER_HEIGHT - 150:
                        self.draw_text_with_shadow(draw, (text_start_x, current_y), line, storyline_font, fill=COLOR_TEXT_LIGHT)
                        current_y += STORYLINE_FONT_SIZE + 8

            # 5. Telegram Watermark (Bottom Right)
            margin = 40
            try:
                telegram_font = ImageFont.truetype(FONT_PATH_REGULAR, WATERMARK_FONT_SIZE) if os.path.exists(FONT_PATH_REGULAR) else ImageFont.load_default()
            except:
                telegram_font = ImageFont.load_default()

            text_width = draw.textlength(CHANNEL_WATERMARK_HANDLE, font=telegram_font)
            bbox = telegram_font.getbbox(CHANNEL_WATERMARK_HANDLE)
            text_height = bbox[3] - bbox[1]

            text_x = POSTER_WIDTH - margin - text_width
            text_y = POSTER_HEIGHT - margin - bbox[3]

            self.draw_text_with_shadow(draw, (text_x, text_y), CHANNEL_WATERMARK_HANDLE, telegram_font, fill=COLOR_TEXT_SUBTLE)

            if self.telegram_logo:
                logo_x = text_x - TELEGRAM_LOGO_SIZE - 10
                logo_y = text_y + (text_height - TELEGRAM_LOGO_SIZE) // 2
                base_image.paste(self.telegram_logo, (int(logo_x), int(logo_y)), self.telegram_logo)

            # 6. Save the final image
            if not output_path:
                os.makedirs(TEMP_FOLDER, exist_ok=True)
                output_path = os.path.join(TEMP_FOLDER, f"{movie_data['movie_id']}_{movie_data['title'].replace(' ', '_')}.jpg")

            base_image = base_image.convert('RGB')
            base_image.save(output_path, 'JPEG', quality=95)
            log.success(f"✅ Glass-themed poster generated successfully: {output_path}")

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

# Global poster generator instance
poster_generator = PosterGenerator()
