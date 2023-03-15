# pylint: disable=import-error
import os, json, csv
from datetime import datetime
from seleniumwire import webdriver
from google.cloud import storage
from google.oauth2 import service_account



def jsonToDict(filePath: str) -> dict:
    with open(filePath, 'r', encoding= 'utf-8') as f:
        s = f.read()
        output = json.loads(s)
    return output

def csvToDict(file: str) -> list:
    output = []
    with open(file, 'r', encoding= 'utf-8') as f:
        rows = csv.DictReader(f)
        for row in rows:
            output.append(row)
    return output

def dictToJson(data, file: str, indent= 0):
    with open(file, 'w+', encoding= 'utf-8') as f:
        json.dump(data, f, ensure_ascii= False, indent= indent)

def createDriver(browser: str, headless = True):
    if browser.lower().strip() == "edge":
        options = webdriver.EdgeOptions()
        if headless == True:
            options.headless = True
        options.add_argument("--inprivate")
        driver = webdriver.Edge(options= options)
        return driver
    elif browser.lower().strip() == "chrome":
        options = webdriver.ChromeOptions()
        if headless == True:
            options.headless = True
        options.add_argument("--incognito")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--start-maximized')
        options.add_argument('--headless')
        driver = webdriver.Chrome(options= options)
        return driver

def uploadGCP(data, dataType: str= "json", service: str = "bucket", destination: str = ""):
    if service.lower().strip() == "bucket":
        if destination != "":
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    os.path.join(os.path.dirname(os.path.dirname(__file__)),"config","bucket.json"),
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                client = storage.Client(project= credentials.project_id, credentials= credentials) 
                bucketName = destination[:destination.find("/")]
                bucket = client.get_bucket(bucketName)
            except Exception as e:
                print(f"issue about {service}:", e)
            else:
                destination = destination.replace(bucketName+"/","")
                blob = bucket.blob(destination)
                if dataType.lower().strip() == "json":
                    blob.upload_from_string(json.dumps(data, ensure_ascii= False, indent= 4), content_type= f"application/{dataType}")
        else:
            print("issue: please insert the destination")



    