SELENIUM_OVERLAY_SELECTORS = [
    "button.cookie__agree",
    "button.cookie-agree",
    "button#cookie-accept",
    "button[aria-label='Accept cookies']",
    ".modal__close",
    ".popup-close",
    "[aria-label='Close']",
    ".fancybox-close",
]

PLAYWRIGHT_OVERLAY_SELECTORS = [
    "button.cookie__agree",
    "button.cookie-agree",
    "button#cookie-accept",
    "button:has-text('Приймаю')",
    "button:has-text('Принять')",
    "button:has-text('Accept')",
    "button:has-text('OK')",
    ".modal__close",
    ".popup-close",
    "[aria-label='Close']",
    ".fancybox-close",
]
