import time
import requests
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from config import (
    BOT_TOKEN, API_ID, API_HASH, MONGO_URI, 
    DATABASE_CHANNEL_ID, MOVIE_CHANNEL_ID, PORT,
    CHANNEL_WATERMARK_HANDLE, LOG_LEVEL
)
import json
from datetime import datetime
from core.logger import log

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            log.info(f"🔍 Received HTTP {self.command} request for path: {self.path}")
            
            if self.path == '/ping':
                log.info("🏓 Processing /ping endpoint")
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK")
                log.success("✅ /ping request handled successfully")
                
            elif self.path == '/':
                log.info("🏠 Processing main status page")
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                
                # Get bot info
                bot_status = "🟢 Online" if self.is_bot_running() else "🔴 Offline"
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Get basic stats (you can enhance this with actual stats from MongoDB)
                stats = self.get_bot_stats()
                
                html_content = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Movie Poster Generator Bot</title>
                    <style>
                        body {{
                            font-family: 'Arial', sans-serif;
                            max-width: 1200px;
                            margin: 0 auto;
                            padding: 20px;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: #333;
                            min-height: 100vh;
                        }}
                        .container {{
                            background: rgba(255, 255, 255, 0.95);
                            padding: 40px;
                            border-radius: 20px;
                            backdrop-filter: blur(10px);
                            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
                            margin-top: 20px;
                        }}
                        h1 {{
                            text-align: center;
                            margin-bottom: 10px;
                            font-size: 2.5em;
                            color: #667eea;
                            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
                        }}
                        .tagline {{
                            text-align: center;
                            font-size: 1.2em;
                            color: #764ba2;
                            margin-bottom: 30px;
                            font-weight: bold;
                        }}
                        .status-card {{
                            background: linear-gradient(135deg, #667eea, #764ba2);
                            color: white;
                            padding: 25px;
                            margin: 20px 0;
                            border-radius: 15px;
                            text-align: center;
                            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
                        }}
                        .status-badge {{
                            display: inline-block;
                            padding: 10px 25px;
                            border-radius: 25px;
                            font-weight: bold;
                            font-size: 1.2em;
                            background: rgba(255, 255, 255, 0.2);
                            margin-bottom: 15px;
                        }}
                        .stats-grid {{
                            display: grid;
                            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                            gap: 20px;
                            margin: 30px 0;
                        }}
                        .stat-item {{
                            background: rgba(255, 255, 255, 0.9);
                            padding: 20px;
                            border-radius: 12px;
                            text-align: center;
                            border-left: 4px solid #667eea;
                            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                        }}
                        .stat-number {{
                            font-size: 2em;
                            font-weight: bold;
                            color: #667eea;
                            margin: 10px 0;
                        }}
                        .info-grid {{
                            display: grid;
                            grid-template-columns: 1fr 1fr;
                            gap: 20px;
                            margin-top: 30px;
                        }}
                        .info-item {{
                            background: rgba(255, 255, 255, 0.8);
                            padding: 20px;
                            border-radius: 12px;
                            border-left: 4px solid #764ba2;
                        }}
                        .feature-grid {{
                            display: grid;
                            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                            gap: 15px;
                            margin-top: 20px;
                        }}
                        .feature-item {{
                            background: linear-gradient(135deg, #667eea, #764ba2);
                            color: white;
                            padding: 15px;
                            border-radius: 10px;
                            text-align: center;
                            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
                        }}
                        .movie-icon {{
                            color: #667eea;
                            font-size: 1.5em;
                            animation: pulse 1.5s ease-in-out infinite;
                        }}
                        @keyframes pulse {{
                            0% {{ transform: scale(1); }}
                            50% {{ transform: scale(1.1); }}
                            100% {{ transform: scale(1); }}
                        }}
                        .footer {{
                            text-align: center;
                            margin-top: 40px;
                            padding-top: 20px;
                            border-top: 1px solid #ddd;
                            color: #636e72;
                        }}
                        h3 {{
                            color: #2d3436;
                            border-bottom: 2px solid #667eea;
                            padding-bottom: 10px;
                        }}
                        .emoji {{
                            font-size: 1.3em;
                            margin-right: 8px;
                        }}
                        .links a {{
                            display: inline-block;
                            margin: 5px 10px;
                            padding: 10px 20px;
                            background: #667eea;
                            color: white;
                            text-decoration: none;
                            border-radius: 25px;
                            transition: all 0.3s;
                        }}
                        .links a:hover {{
                            background: #764ba2;
                            transform: translateY(-2px);
                        }}
                        .channel-info {{
                            background: linear-gradient(135deg, #ffd89b, #19547b);
                            color: white;
                            padding: 15px;
                            border-radius: 10px;
                            margin: 10px 0;
                            text-align: center;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>🎬 Movie Poster Generator Bot</h1>
                        <div class="tagline">Automatically Generate Stunning Movie Posters from TMDB Data</div>
                        
                        <div class="status-card">
                            <div class="status-badge">
                                <span class="movie-icon">🎭</span> {bot_status} <span class="movie-icon">🎭</span>
                            </div>
                            <p><strong>Last Updated:</strong> {current_time}</p>
                            <p><strong>Port:</strong> {PORT}</p>
                            <p><strong>Watermark:</strong> {CHANNEL_WATERMARK_HANDLE}</p>
                        </div>
                        
                        <div class="stats-grid">
                            <div class="stat-item">
                                <div class="emoji">📊</div>
                                <div class="stat-number">{stats['total_movies']}</div>
                                <div>Movies Processed</div>
                            </div>
                            <div class="stat-item">
                                <div class="emoji">🔄</div>
                                <div class="stat-number">{stats['cache_hits']}</div>
                                <div>Cache Hits</div>
                            </div>
                            <div class="stat-item">
                                <div class="emoji">⚡</div>
                                <div class="stat-number">{stats['active_requests']}</div>
                                <div>Active Requests</div>
                            </div>
                            <div class="stat-item">
                                <div class="emoji">🎯</div>
                                <div class="stat-number">{stats['success_rate']}%</div>
                                <div>Success Rate</div>
                            </div>
                        </div>
                        
                        <div class="info-grid">
                            <div class="info-item">
                                <h3>🤖 Bot Configuration</h3>
                                <p><strong>API ID:</strong> {API_ID if 0 else 'Configured'}</p>
                                <p><strong>API Hash:</strong> {'*' * len(API_HASH) if API_HASH else 'Not set'}</p>
                                <p><strong>Bot Token:</strong> {BOT_TOKEN[:15] + '...' if BOT_TOKEN else 'Not set'}</p>
                                <p><strong>MongoDB:</strong> {'Connected' if MONGO_URI else 'Not configured'}</p>
                                <p><strong>Log Level:</strong> {LOG_LEVEL}</p>
                            </div>
                            
                            <div class="info-item">
                                <h3>📺 Channel Info</h3>
                                <div class="channel-info">
                                    <strong>Database Channel:</strong> {DATABASE_CHANNEL_ID}
                                </div>
                                <div class="channel-info">
                                    <strong>Movie Channel:</strong> {MOVIE_CHANNEL_ID}
                                </div>
                                <p><strong>Watermark:</strong> {CHANNEL_WATERMARK_HANDLE}</p>
                                <p><strong>Poster Size:</strong> 1280×720 pixels</p>
                            </div>
                        </div>
                        
                        <div class="info-item">
                            <h3>🚀 Core Features</h3>
                            <div class="feature-grid">
                                <div class="feature-item">
                                    <span class="emoji">🎬</span> Auto Movie Detection
                                </div>
                                <div class="feature-item">
                                    <span class="emoji">🖼️</span> Poster Generation
                                </div>
                                <div class="feature-item">
                                    <span class="emoji">⚡</span> TMDB Integration
                                </div>
                                <div class="feature-item">
                                    <span class="emoji">💾</span> MongoDB Caching
                                </div>
                                <div class="feature-item">
                                    <span class="emoji">📱</span> Telegram Bot
                                </div>
                                <div class="feature-item">
                                    <span class="emoji">🎯</span> Smart Search
                                </div>
                                <div class="feature-item">
                                    <span class="emoji">🔍</span> Year Detection
                                </div>
                                <div class="feature-item">
                                    <span class="emoji">📊</span> Detailed Logging
                                </div>
                            </div>
                        </div>
                        
                        <div class="info-item">
                            <h3>📋 How to Use</h3>
                            <ol style="line-height: 1.8;">
                                <li><strong>Direct Message:</strong> Send movie name directly to the bot</li>
                                <li><strong>Database Channel:</strong> Forward movie files to the database channel</li>
                                <li><strong>Auto-detection:</strong> Bot detects movie titles from filenames, captions, or text</li>
                                <li><strong>Poster Generation:</strong> Bot creates 1280×720 posters with TMDB data</li>
                                <li><strong>Channel Posting:</strong> Generated posters are posted to movie channel with download button</li>
                            </ol>
                        </div>
                        
                        <div class="info-item">
                            <h3>🔧 Technical Stack</h3>
                            <div class="feature-grid">
                                <div class="feature-item">
                                    <span class="emoji">🐍</span> Python Pyrogram
                                </div>
                                <div class="feature-item">
                                    <span class="emoji">🎭</span> TMDB API
                                </div>
                                <div class="feature-item">
                                    <span class="emoji">🍃</span> MongoDB
                                </div>
                                <div class="feature-item">
                                    <span class="emoji">🖼️</span> Pillow (PIL)
                                </div>
                                <div class="feature-item">
                                    <span class="emoji">📝</span> Loguru
                                </div>
                                <div class="feature-item">
                                    <span class="emoji">🌐</span> HTTP Server
                                </div>
                            </div>
                        </div>
                        
                        <div class="footer">
                            <p>⚡ Powered by Pyrogram, TMDB API & MongoDB</p>
                            <p>🎬 Professional Movie Poster Generation • 🕒 24/7 Uptime</p>
                            <p style="margin-top: 10px; font-size: 0.9em;">
                                "Transform movie requests into stunning posters automatically! 🎭"
                            </p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                self.wfile.write(html_content.encode('utf-8'))
                log.success("✅ Main status page sent successfully")
                
            elif self.path == '/stats':
                log.info("📊 Processing /stats endpoint")
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                
                stats = self.get_bot_stats()
                self.wfile.write(json.dumps(stats, indent=2).encode('utf-8'))
                log.success("✅ /stats request handled successfully")
                
            else:
                log.warning(f"❌ Unknown path requested: {self.path}")
                self.send_response(404)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"404 - Page not found")
                
        except Exception as e:
            log.error(f"💥 Error handling request {self.path}: {e}")
            try:
                self.send_response(500)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"500 - Internal Server Error")
            except Exception as send_error:
                log.critical(f"🚨 Failed to send error response: {send_error}")

    def is_bot_running(self):
        """Check if the bot is running."""
        try:
            # Add actual bot status check logic here
            # For now, we'll assume it's running if we can handle requests
            return True
        except Exception as e:
            log.error(f"❌ Error checking bot status: {e}")
            return False

    def get_bot_stats(self):
        """Get bot statistics (you can enhance this with real MongoDB queries)."""
        try:
            # Placeholder stats - replace with actual database queries
            stats = {
                'total_movies': 0,
                'cache_hits': 0,
                'active_requests': 0,
                'success_rate': 95,
                'uptime': str(datetime.now()),
                'version': '1.0.0'
            }
            
            # You can add real MongoDB queries here later:
            # from database.mongo_client import db
            # stats['total_movies'] = db.movies.count_documents({})
            # stats['cache_hits'] = db.requests.count_documents({'status': 'cached'})
            
            return stats
            
        except Exception as e:
            log.error(f"❌ Error getting bot stats: {e}")
            return {
                'total_movies': 'N/A',
                'cache_hits': 'N/A',
                'active_requests': 'N/A',
                'success_rate': 'N/A',
                'uptime': str(datetime.now()),
                'version': '1.0.0'
            }

    def log_message(self, format, *args):
        """Override to use loguru instead of default logging."""
        log.info(f"🌐 HTTP {self.command} {self.path} - {self.client_address[0]}")

def run_health_server():
    """Run a simple HTTP server to respond to health checks and display bot info."""
    try:
        log.info(f"🚀 Starting health server on port {PORT}...")
        
        server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
        log.success(f"🌐 Health server started successfully on port {PORT}")
        log.info(f"🎬 Status page: http://0.0.0.0:{PORT}/")
        log.info(f"📊 Stats API: http://0.0.0.0:{PORT}/stats")
        log.info(f"🏓 Health check: http://0.0.0.0:{PORT}/ping")
        
        server.serve_forever()
        
    except OSError as e:
        if "Address already in use" in str(e):
            log.error(f"💥 Port {PORT} is already in use! Please use a different port.")
        else:
            log.error(f"💥 OSError starting health server: {e}")
        raise
    except Exception as e:
        log.critical(f"💥 Failed to start health server: {e}")
        raise

def start_keep_alive():
    """Start the keep-alive system with health server and periodic pings."""
    try:
        log.info("🔗 Starting keep-alive system for Movie Poster Bot...")
        log.info(f"📊 Will run on port: {PORT}")
        log.info(f"🏠 Status page: http://localhost:{PORT}/")
        
        # Start health server in a separate thread
        health_thread = threading.Thread(target=run_health_server, daemon=True)
        health_thread.name = "MovieBotHealthServer"
        
        log.info("▶️ Starting health server thread...")
        health_thread.start()
        log.success("✅ Health server thread started successfully")
        
        # Give the server a moment to start
        time.sleep(2)
        
        # Periodic pings to keep the server alive
        log.info("🔄 Starting periodic ping loop...")
        session = requests.Session()
        ping_count = 0
        
        while True:
            try:
                ping_count += 1
                log.debug(f"🏓 Sending keep-alive ping #{ping_count}...")
                
                # Ping the local health endpoint
                response = session.get(f'http://localhost:{PORT}/ping', timeout=5)
                
                if response.status_code == 200:
                    log.success(f"✅ Keep-alive ping #{ping_count} successful")
                else:
                    log.warning(f"⚠️ Keep-alive ping #{ping_count} returned status: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                log.warning(f"⏰ Keep-alive ping #{ping_count} timed out")
            except requests.exceptions.ConnectionError:
                log.error(f"🔌 Keep-alive ping #{ping_count} connection error - server may not be ready")
            except Exception as e:
                log.error(f"💥 Keep-alive ping #{ping_count} failed: {e}")
            
            # Ping every 5 minutes (300 seconds)
            time.sleep(300)
            
    except Exception as e:
        log.critical(f"💥 Keep-alive system crashed: {e}")
        raise

if __name__ == "__main__":
    log.info("🔧 Running keep_alive.py as standalone script")
    start_keep_alive()