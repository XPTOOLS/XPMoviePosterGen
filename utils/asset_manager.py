import os
from core.logger import log
from config import FONT_PATH_BOLD, FONT_PATH_REGULAR

class AssetManager:
    def __init__(self):
        self.assets_ready = False
    
    def check_assets(self):
        """Check if all required assets are available"""
        try:
            log.info("📁 Checking assets...")
            
            # Check fonts
            bold_font_exists = os.path.exists(FONT_PATH_BOLD)
            regular_font_exists = os.path.exists(FONT_PATH_REGULAR)
            
            if not bold_font_exists:
                log.warning(f"⚠️ Bold font not found: {FONT_PATH_BOLD}")
            if not regular_font_exists:
                log.warning(f"⚠️ Regular font not found: {FONT_PATH_REGULAR}")
            
            
            # Summary
            if bold_font_exists and regular_font_exists:
                log.success("✅ All assets found and ready!")
                self.assets_ready = True
            else:
                log.warning("🎨 Some assets missing - will use fallbacks")
                self.assets_ready = False
            
            return self.assets_ready
            
        except Exception as e:
            log.error(f"💥 Error checking assets: {e}")
            self.assets_ready = False
            return False

# Global asset manager instance
asset_manager = AssetManager()
