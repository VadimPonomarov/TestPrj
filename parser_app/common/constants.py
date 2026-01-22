HOME_URL = "https://brain.com.ua/ukr/"
DEFAULT_QUERY = "Apple iPhone 15 128GB Black"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

REQUEST_HEADERS = {"User-Agent": USER_AGENT}

HOME_SEARCH_INPUT_XPATH = "/html/body/header/div[1]/div/div/div[2]/form/input[1]"
HOME_SEARCH_SUBMIT_XPATH = "/html/body/header/div[1]/div/div/div[2]/form/input[2]"

HOME_SEARCH_INPUT_XPATH_FALLBACK = "/html/body/header/div[2]/div/div/div[2]/form/input[1]"
HOME_SEARCH_SUBMIT_XPATH_FALLBACK = "/html/body/header/div[2]/div/div/div[2]/form/input[2]"

SEARCH_FIRST_PRODUCT_LINK_XPATH = (
    "//a[contains(@href,'-p') and contains(@href,'.html') and normalize-space(string(.))!=''][1]"
)

PRODUCT_CODE_XPATH = "//div[@id='product_code']//span[contains(@class,'br-pr-code-val')]"
REVIEW_ANCHOR_XPATH = "//a[contains(@href,'#reviews')][1]"

COLOR_VALUE_XPATH = "//span[normalize-space()='Колір']/following-sibling::span[1]//a[1]"
STORAGE_VALUE_XPATH = "//span[normalize-space()=\"Вбудована пам'ять\" or normalize-space()=\"Вбудована пам\u2019ять\"]/following-sibling::span[1]//a[1]"
SCREEN_DIAGONAL_XPATH = "//span[normalize-space()='Діагональ екрану']/following-sibling::span[1]//a[1]"
DISPLAY_RESOLUTION_XPATH = "//span[normalize-space()='Роздільна здатність екрану']/following-sibling::span[1]//a[1]"

CHARACTERISTICS_ROWS_XPATH = "//div[@id='br-pr-7']//div[contains(@class,'br-pr-chr')]//div[count(span)>=2]"
CHARACTERISTICS_KEY_REL_XPATH = "./span[1]"
CHARACTERISTICS_VALUE_REL_XPATH = "./span[2]"

IMAGES_XPATH = "//div[contains(@class,'main-pictures-block')]//img[@src]/@src"

PRICE_XPATH = "(//div[contains(@class,'br-pp-price')])[1]//span[1]"
OLD_PRICE_XPATH = "//div[contains(@class,'old-price')]//span[1]"

ALL_CHARACTERISTICS_BUTTON_XPATH = "//div[@id='br-characteristics']//button[contains(@class,'br-prs-button')][.//span[contains(.,'Всі характеристики')]]"
CHARACTERISTICS_ANCHOR_XPATH = "//a[@href='#br-characteristics']"
CHARACTERISTICS_WRAPPER_XPATH = "//div[@id='br-characteristics']"
