from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import undetected_chromedriver as uc
from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from app.config import settings


class MeetBot:
    def __init__(
        self,
        profile_dir: Path | None = None,
        chrome_binary: Path | None = None,
        extension_path: Path | None = None,
    ) -> None:
        options = uc.ChromeOptions()

        if chrome_binary:
            options.binary_location = str(chrome_binary)

        if profile_dir:
            options.add_argument(f"--user-data-dir={str(profile_dir)}")

        # Stealth options
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-infobars")
        options.add_argument("--lang=en-US")

        # Load the extension for audio capture
        if extension_path and Path(extension_path).exists():
            options.add_argument(f"--load-extension={str(extension_path)}")

        # Auto grant mic/camera prompts (we keep them off in UI anyway)
        options.add_argument("--use-fake-ui-for-media-stream")

        self.driver = uc.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 30)

    def _click_if_present(self, by: By, value: str) -> bool:
        try:
            elem = self.wait.until(EC.element_to_be_clickable((by, value)))
            elem.click()
            return True
        except Exception:
            return False

    def join(self, meeting_url: str) -> None:
        logger.info(f"Navigating to {meeting_url}")
        self.driver.get(meeting_url)

        # Ensure camera/mic toggles are off before joining
        self._disable_av()

        # Click Join now / Ask to join
        if not self._click_if_present(By.XPATH, "//span[text()='Join now' or text()='Ask to join']/ancestor::button"):
            # Fallback: button with aria-label
            self._click_if_present(By.XPATH, "//button[@aria-label='Join now' or @aria-label='Ask to join']")

        logger.info("Join action invoked; waiting a bit for meeting to load")
        time.sleep(5)

        # Enable captions for better transcript via DOM (optional)
        self._enable_captions_if_possible()

    def _disable_av(self) -> None:
        # Camera off
        self._click_if_present(By.XPATH, "//div[@role='button' and @aria-label='Turn off camera' or @aria-label='Turn on camera']")
        # Mic off
        self._click_if_present(By.XPATH, "//div[@role='button' and @aria-label='Turn off microphone' or @aria-label='Turn on microphone']")

    def _enable_captions_if_possible(self) -> None:
        # Try to toggle captions (English)
        self._click_if_present(By.XPATH, "//button[@aria-label='Turn on captions (c)']")

    def close(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            pass


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Google Meet bot joiner")
    parser.add_argument("meeting_url", help="Google Meet URL")
    parser.add_argument("--profile", dest="profile", default=str(settings.chrome_profile_path or ""))
    parser.add_argument("--chrome", dest="chrome", default=str(settings.chrome_binary_path or ""))
    parser.add_argument("--extension", dest="extension", default=str(settings.extension_path or ""))
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    bot = MeetBot(
        profile_dir=Path(args.profile) if args.profile else None,
        chrome_binary=Path(args.chrome) if args.chrome else None,
        extension_path=Path(args.extension) if args.extension else None,
    )
    try:
        bot.join(args.meeting_url)
        logger.info("Bot joined. Press Ctrl+C to exit.")
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        bot.close()