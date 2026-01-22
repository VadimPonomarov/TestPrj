SELENIUM_OVERLAY_SELECTORS = [
    "//button[contains(concat(' ', normalize-space(@class), ' '), ' cookie__agree ')]",
    "//button[contains(concat(' ', normalize-space(@class), ' '), ' cookie-agree ')]",
    "//button[@id='cookie-accept']",
    "//button[@aria-label='Accept cookies']",
    "//*[contains(concat(' ', normalize-space(@class), ' '), ' modal__close ')]",
    "//*[contains(concat(' ', normalize-space(@class), ' '), ' popup-close ')]",
    "//*[@aria-label='Close']",
    "//*[contains(concat(' ', normalize-space(@class), ' '), ' fancybox-close ')]",
]

PLAYWRIGHT_OVERLAY_SELECTORS = [
    "//button[contains(concat(' ', normalize-space(@class), ' '), ' cookie__agree ')]",
    "//button[contains(concat(' ', normalize-space(@class), ' '), ' cookie-agree ')]",
    "//button[@id='cookie-accept']",
    "//button[contains(normalize-space(string(.)), 'Приймаю')]",
    "//button[contains(normalize-space(string(.)), 'Принять')]",
    "//button[contains(normalize-space(string(.)), 'Accept')]",
    "//button[contains(normalize-space(string(.)), 'OK')]",
    "//*[contains(concat(' ', normalize-space(@class), ' '), ' modal__close ')]",
    "//*[contains(concat(' ', normalize-space(@class), ' '), ' popup-close ')]",
    "//*[@aria-label='Close']",
    "//*[contains(concat(' ', normalize-space(@class), ' '), ' fancybox-close ')]",
]
