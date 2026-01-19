from django.apps import AppConfig
import os
import threading


_playwright_warmup_started = False
_selenium_warmup_started = False


class ParserAppConfig(AppConfig):
    name = "parser_app"

    def ready(self):  # type: ignore[override]
        global _playwright_warmup_started
        global _selenium_warmup_started

        # When Django autoreloader is enabled, only run in the main (reloaded) process.
        run_main = os.getenv("RUN_MAIN")
        if run_main is not None and run_main != "true":
            return

        if os.getenv("PLAYWRIGHT_WARMUP_ON_STARTUP", "1").strip() not in {"0", "false", "False", "no", "NO"}:
            if not _playwright_warmup_started:
                _playwright_warmup_started = True

                def _warmup():
                    try:
                        from parser_app.parsers.playwright.runtime import run_in_browser_thread
                        from parser_app.parsers.playwright.context import create_page
                        from parser_app.parsers.config import HOME_URL

                        async def _job(browser):
                            _, context, page = await create_page(browser=browser)
                            try:
                                await page.goto(HOME_URL, wait_until="domcontentloaded")
                            finally:
                                try:
                                    await context.close()
                                except Exception:
                                    pass

                        run_in_browser_thread(_job)
                    except Exception:
                        return

                threading.Thread(target=_warmup, name="playwright-warmup", daemon=True).start()

        if os.getenv("SELENIUM_WARMUP_ON_STARTUP", "1").strip() not in {"0", "false", "False", "no", "NO"}:
            if os.getenv("SELENIUM_REUSE_DRIVER", "").strip() in {"1", "true", "True", "yes", "YES"}:
                if not _selenium_warmup_started:
                    _selenium_warmup_started = True

                    def _selenium_warmup():
                        try:
                            from parser_app.parsers.config import HOME_URL
                            from parser_app.parsers.selenium.runtime import get_driver

                            driver = get_driver()
                            try:
                                driver.get(HOME_URL)
                            except Exception:
                                pass
                        except Exception:
                            return

                    threading.Thread(target=_selenium_warmup, name="selenium-warmup", daemon=True).start()
