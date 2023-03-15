from seleniumwire import webdriver

options = webdriver.Chrome()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(options= options)
driver.get("https://google.com.vn")




