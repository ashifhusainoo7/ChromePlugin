"""
Enterprise Google Meet Bot - Selenium Automation
Advanced bot implementation with anti-detection capabilities for automated meeting joining
"""

import asyncio
import logging
import time
import random
import json
import os
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from urllib.parse import urlparse

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementClickInterceptedException,
    WebDriverException
)


@dataclass
class MeetingConfig:
    """Configuration for meeting automation"""
    mute_on_join: bool = True
    disable_video: bool = True
    auto_accept_permissions: bool = True
    recording_enabled: bool = True
    stealth_mode: bool = True
    user_agent_override: Optional[str] = None
    display_name: Optional[str] = None


@dataclass
class BotStatus:
    """Current status of the bot"""
    is_active: bool = False
    current_meeting: Optional[str] = None
    participants_count: int = 0
    session_duration: float = 0
    last_error: Optional[str] = None


class MeetBotException(Exception):
    """Custom exception for Meet Bot errors"""
    pass


class AdvancedMeetBot:
    """
    Enterprise-grade Google Meet automation bot with advanced anti-detection
    """
    
    def __init__(self, config: MeetingConfig = None, headless: bool = False):
        self.config = config or MeetingConfig()
        self.headless = headless
        self.driver: Optional[uc.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.status = BotStatus()
        
        # Anti-detection configuration
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Set up enterprise-level logging"""
        logger = logging.getLogger('MeetBot')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # File handler
            file_handler = logging.FileHandler('selenium-bot/logs/meet_bot.log')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter('%(levelname)s: %(message)s')
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        return logger

    async def initialize(self) -> bool:
        """
        Initialize the Chrome driver with advanced anti-detection
        """
        try:
            self.logger.info("Initializing Chrome driver with anti-detection measures...")
            
            # Chrome options for stealth
            options = uc.ChromeOptions()
            
            if self.headless:
                options.add_argument('--headless=new')
            
            # Anti-detection options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--disable-extensions-file-access-check')
            options.add_argument('--disable-extensions-http-throttling')
            options.add_argument('--disable-ipc-flooding-protection')
            
            # Media permissions for audio/video
            prefs = {
                "profile.default_content_setting_values": {
                    "media_stream_mic": 1,
                    "media_stream_camera": 1,
                    "notifications": 1
                },
                "profile.default_content_settings.popups": 0,
                "profile.managed_default_content_settings.images": 2  # Block images for performance
            }
            options.add_experimental_option("prefs", prefs)
            
            # User agent randomization
            if self.config.user_agent_override:
                options.add_argument(f'--user-agent={self.config.user_agent_override}')
            else:
                options.add_argument(f'--user-agent={random.choice(self.user_agents)}')
            
            # Initialize undetected Chrome
            self.driver = uc.Chrome(
                options=options,
                version_main=None,  # Auto-detect Chrome version
                driver_executable_path=None  # Auto-download driver
            )
            
            # Execute stealth scripts
            await self._execute_stealth_scripts()
            
            # Set up WebDriverWait
            self.wait = WebDriverWait(self.driver, 30)
            
            self.logger.info("Chrome driver initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {str(e)}")
            self.status.last_error = str(e)
            return False

    async def _execute_stealth_scripts(self):
        """Execute JavaScript to enhance stealth capabilities"""
        stealth_scripts = [
            # Remove webdriver property
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            
            # Mock plugins
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            """,
            
            # Mock languages
            """
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            """,
            
            # Mock permissions
            """
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
            """
        ]
        
        for script in stealth_scripts:
            try:
                self.driver.execute_script(script)
            except Exception as e:
                self.logger.warning(f"Failed to execute stealth script: {str(e)}")

    async def join_meeting(self, meeting_url: str, display_name: str = None) -> bool:
        """
        Join a Google Meet meeting with advanced automation
        """
        try:
            self.logger.info(f"Attempting to join meeting: {meeting_url}")
            
            if not self.driver:
                raise MeetBotException("Driver not initialized")
            
            # Validate meeting URL
            if not self._is_valid_meet_url(meeting_url):
                raise MeetBotException(f"Invalid Google Meet URL: {meeting_url}")
            
            # Navigate to meeting
            self.driver.get(meeting_url)
            await asyncio.sleep(random.uniform(2, 4))  # Random delay
            
            # Handle potential login requirement
            if await self._handle_login_if_required():
                await asyncio.sleep(3)
            
            # Set display name if provided
            if display_name or self.config.display_name:
                await self._set_display_name(display_name or self.config.display_name)
            
            # Configure audio/video settings
            await self._configure_media_settings()
            
            # Join the meeting
            if await self._click_join_button():
                self.status.is_active = True
                self.status.current_meeting = meeting_url
                self.logger.info("Successfully joined the meeting")
                
                # Post-join configuration
                await self._post_join_setup()
                
                return True
            else:
                raise MeetBotException("Failed to join meeting")
                
        except Exception as e:
            self.logger.error(f"Failed to join meeting: {str(e)}")
            self.status.last_error = str(e)
            return False

    def _is_valid_meet_url(self, url: str) -> bool:
        """Validate Google Meet URL"""
        try:
            parsed = urlparse(url)
            return (
                parsed.netloc == 'meet.google.com' and
                len(parsed.path) > 1 and
                parsed.scheme in ['http', 'https']
            )
        except Exception:
            return False

    async def _handle_login_if_required(self) -> bool:
        """Handle Google account login if required"""
        try:
            # Check if already logged in
            if "accounts.google.com" in self.driver.current_url:
                self.logger.warning("Google login required - bot may be detected")
                # For enterprise deployment, implement proper OAuth flow
                return False
            
            # Check for sign-in prompts
            sign_in_selectors = [
                'a[data-action="sign in"]',
                'button[data-action="sign in"]',
                '.sign-in-button'
            ]
            
            for selector in sign_in_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        self.logger.info("Sign-in prompt detected but skipping...")
                        # In enterprise deployment, handle authentication
                        return False
                except NoSuchElementException:
                    continue
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling login: {str(e)}")
            return False

    async def _set_display_name(self, name: str):
        """Set display name for the meeting"""
        try:
            name_selectors = [
                'input[placeholder*="name"]',
                'input[aria-label*="name"]',
                'input[data-testid="user-name"]',
                '.name-input input'
            ]
            
            for selector in name_selectors:
                try:
                    name_input = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    
                    # Clear existing name and type new one
                    name_input.clear()
                    await self._human_type(name_input, name)
                    
                    self.logger.info(f"Display name set to: {name}")
                    return
                    
                except TimeoutException:
                    continue
                    
            self.logger.warning("Could not find name input field")
            
        except Exception as e:
            self.logger.error(f"Failed to set display name: {str(e)}")

    async def _configure_media_settings(self):
        """Configure microphone and camera settings"""
        try:
            # Find microphone toggle
            if self.config.mute_on_join:
                await self._toggle_microphone(False)
            
            # Find camera toggle
            if self.config.disable_video:
                await self._toggle_camera(False)
                
            await asyncio.sleep(random.uniform(1, 2))
            
        except Exception as e:
            self.logger.error(f"Failed to configure media settings: {str(e)}")

    async def _toggle_microphone(self, enable: bool):
        """Toggle microphone on/off"""
        mic_selectors = [
            '[data-is-muted]',
            '[aria-label*="microphone"]',
            '[aria-label*="Mute"]',
            'button[data-tooltip*="microphone"]',
            '.mic-button'
        ]
        
        for selector in mic_selectors:
            try:
                mic_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                if mic_button.is_displayed():
                    is_muted = (
                        mic_button.get_attribute('data-is-muted') == 'true' or
                        'muted' in mic_button.get_attribute('class').lower() or
                        mic_button.get_attribute('aria-pressed') == 'true'
                    )
                    
                    # Click if state needs to change
                    if (enable and is_muted) or (not enable and not is_muted):
                        await self._safe_click(mic_button)
                        self.logger.info(f"Microphone {'enabled' if enable else 'muted'}")
                    
                    return
                    
            except (NoSuchElementException, ElementClickInterceptedException):
                continue
                
        self.logger.warning("Could not find microphone toggle")

    async def _toggle_camera(self, enable: bool):
        """Toggle camera on/off"""
        camera_selectors = [
            '[aria-label*="camera"]',
            '[aria-label*="video"]',
            'button[data-tooltip*="camera"]',
            '.video-button'
        ]
        
        for selector in camera_selectors:
            try:
                camera_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                if camera_button.is_displayed():
                    is_disabled = (
                        camera_button.get_attribute('data-is-muted') == 'true' or
                        'disabled' in camera_button.get_attribute('class').lower() or
                        camera_button.get_attribute('aria-pressed') == 'true'
                    )
                    
                    # Click if state needs to change
                    if (enable and is_disabled) or (not enable and not is_disabled):
                        await self._safe_click(camera_button)
                        self.logger.info(f"Camera {'enabled' if enable else 'disabled'}")
                    
                    return
                    
            except (NoSuchElementException, ElementClickInterceptedException):
                continue
                
        self.logger.warning("Could not find camera toggle")

    async def _click_join_button(self) -> bool:
        """Click the join meeting button"""
        join_selectors = [
            'button[data-testid="join-meeting"]',
            'button[jsname="Qx7uuf"]',  # Google Meet specific
            'span:contains("Join now")',
            'span:contains("Ask to join")',
            '[aria-label*="Join"]',
            '.join-button'
        ]
        
        for selector in join_selectors:
            try:
                if ':contains(' in selector:
                    # XPath for text content
                    xpath = f"//span[contains(text(), '{selector.split('\"')[1]}')]"
                    join_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                else:
                    join_button = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                
                await self._safe_click(join_button)
                self.logger.info("Join button clicked")
                
                # Wait for meeting to load
                await asyncio.sleep(random.uniform(3, 5))
                return True
                
            except TimeoutException:
                continue
            except Exception as e:
                self.logger.warning(f"Error clicking join button: {str(e)}")
                continue
        
        self.logger.error("Could not find or click join button")
        return False

    async def _post_join_setup(self):
        """Configuration after joining the meeting"""
        try:
            # Dismiss any welcome dialogs
            await self._dismiss_dialogs()
            
            # Enable gallery view for better participant monitoring
            await self._set_gallery_view()
            
            # Hide self view if possible
            await self._hide_self_view()
            
            self.logger.info("Post-join setup completed")
            
        except Exception as e:
            self.logger.error(f"Post-join setup failed: {str(e)}")

    async def _dismiss_dialogs(self):
        """Dismiss welcome dialogs and notifications"""
        dialog_selectors = [
            '.dismiss-button',
            '[aria-label*="Dismiss"]',
            '[aria-label*="Close"]',
            '.notification-close',
            'button[data-testid="dismiss"]'
        ]
        
        for selector in dialog_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        await self._safe_click(element)
                        await asyncio.sleep(0.5)
            except Exception:
                continue

    async def _set_gallery_view(self):
        """Switch to gallery view for better monitoring"""
        view_selectors = [
            '[aria-label*="Gallery"]',
            '[aria-label*="Grid"]',
            'button[data-tooltip*="gallery"]'
        ]
        
        for selector in view_selectors:
            try:
                view_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                if view_button.is_displayed():
                    await self._safe_click(view_button)
                    self.logger.info("Switched to gallery view")
                    return
            except Exception:
                continue

    async def _hide_self_view(self):
        """Hide self view to be less conspicuous"""
        try:
            # Find self view and hide it
            self_view_script = """
            const selfViews = document.querySelectorAll('[data-self-name], .self-view, [aria-label*="You"]');
            selfViews.forEach(view => {
                if (view.closest('.participant-container')) {
                    view.closest('.participant-container').style.display = 'none';
                }
            });
            """
            self.driver.execute_script(self_view_script)
            
        except Exception as e:
            self.logger.warning(f"Could not hide self view: {str(e)}")

    async def _safe_click(self, element):
        """Safely click an element with human-like behavior"""
        try:
            # Scroll to element
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Move to element and click
            actions = ActionChains(self.driver)
            actions.move_to_element(element).pause(random.uniform(0.1, 0.2)).click().perform()
            
        except Exception as e:
            # Fallback to JavaScript click
            self.driver.execute_script("arguments[0].click();", element)

    async def _human_type(self, element, text: str):
        """Type text with human-like timing"""
        element.clear()
        for char in text:
            element.send_keys(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))

    async def get_participants(self) -> List[Dict]:
        """Get list of meeting participants"""
        try:
            participants = []
            
            # Try different selectors for participant information
            participant_selectors = [
                '[data-participant-id]',
                '.participant-name',
                '[aria-label*="participant"]'
            ]
            
            for selector in participant_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        name = element.text.strip() or element.get_attribute('aria-label')
                        if name and name not in [p['name'] for p in participants]:
                            participants.append({
                                'name': name,
                                'id': element.get_attribute('data-participant-id') or f"participant_{len(participants)}",
                                'is_host': 'host' in element.get_attribute('class').lower() if element.get_attribute('class') else False
                            })
                    except Exception:
                        continue
            
            self.status.participants_count = len(participants)
            return participants
            
        except Exception as e:
            self.logger.error(f"Failed to get participants: {str(e)}")
            return []

    async def monitor_meeting(self) -> Dict:
        """Monitor meeting status and return current state"""
        try:
            # Check if still in meeting
            if not self._is_in_meeting():
                self.status.is_active = False
                return {'status': 'ended', 'error': 'Meeting ended or connection lost'}
            
            # Get participant count
            participants = await self.get_participants()
            
            # Check for meeting end indicators
            end_indicators = [
                '[data-call-ended]',
                '.meeting-ended',
                '.call-ended'
            ]
            
            for selector in end_indicators:
                try:
                    if self.driver.find_element(By.CSS_SELECTOR, selector):
                        self.status.is_active = False
                        return {'status': 'ended', 'reason': 'Meeting terminated'}
                except NoSuchElementException:
                    continue
            
            return {
                'status': 'active',
                'participants': len(participants),
                'meeting_url': self.status.current_meeting,
                'duration': time.time() - getattr(self, 'join_time', time.time())
            }
            
        except Exception as e:
            self.logger.error(f"Meeting monitoring failed: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def _is_in_meeting(self) -> bool:
        """Check if currently in a meeting"""
        try:
            # Check URL and page elements
            current_url = self.driver.current_url
            return (
                'meet.google.com' in current_url and
                len(current_url.split('/')[-1]) > 5 and
                self.driver.find_elements(By.CSS_SELECTOR, '[data-call-ended]') == []
            )
        except Exception:
            return False

    async def leave_meeting(self):
        """Leave the current meeting"""
        try:
            if not self.status.is_active:
                return True
            
            leave_selectors = [
                '[aria-label*="Leave call"]',
                '[aria-label*="End call"]',
                '.leave-button',
                'button[data-testid="end-call"]'
            ]
            
            for selector in leave_selectors:
                try:
                    leave_button = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    await self._safe_click(leave_button)
                    
                    self.status.is_active = False
                    self.status.current_meeting = None
                    self.logger.info("Left the meeting")
                    return True
                    
                except TimeoutException:
                    continue
            
            # Fallback: close the tab
            self.driver.close()
            self.status.is_active = False
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to leave meeting: {str(e)}")
            return False

    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.status.is_active:
                await self.leave_meeting()
            
            if self.driver:
                self.driver.quit()
                self.driver = None
            
            self.logger.info("Bot cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")

    def get_status(self) -> BotStatus:
        """Get current bot status"""
        return self.status


# Utility functions for the bot
async def create_meet_bot(headless: bool = True, config: MeetingConfig = None) -> AdvancedMeetBot:
    """Factory function to create and initialize a Meet bot"""
    bot = AdvancedMeetBot(config=config, headless=headless)
    if await bot.initialize():
        return bot
    else:
        raise MeetBotException("Failed to initialize Meet bot")


if __name__ == "__main__":
    # Example usage
    async def main():
        config = MeetingConfig(
            mute_on_join=True,
            disable_video=True,
            display_name="Sentiment Bot"
        )
        
        bot = await create_meet_bot(headless=False, config=config)
        
        try:
            # Join meeting
            meeting_url = "https://meet.google.com/your-meeting-code"
            success = await bot.join_meeting(meeting_url)
            
            if success:
                # Monitor for 10 seconds
                for _ in range(10):
                    status = await bot.monitor_meeting()
                    print(f"Meeting status: {status}")
                    await asyncio.sleep(1)
        
        finally:
            await bot.cleanup()
    
    # Run the example
    asyncio.run(main())