import os, sys, grequests, json, csv, time
import zlib
from datetime import datetime
from googlesearch import search


ecommerceDir = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ecommerceDir)

inputDir = os.path.join(ecommerceDir, 'input')
outputDir = os.path.join(ecommerceDir, 'output')

from utils.assistant import *
configs = jsonToDict(os.path.join(ecommerceDir, "config", "url.json"))

def shopeeGetShops(countryCodes: list) -> list:
    """
    This function returns the list of shops from hot items
    """
    for countryCode in countryCodes:
        countryCode = countryCode.upper()
        if len(countryCode) != 3:
            print(f"issue: The length of countryCode {countryCode} must be 3.")
            return None        
        else:
            shopids = set()
            categories = configs['SHOPEE']['CATEGORIES']
            for cate in categories:
                for sort in ['pop','sales']:
                    page = 0
                    stop = 0
                    while stop == 0:
                        url = cate['URL'][countryCode].format(page,sort)
                        driver = createDriver('edge')
                        driver.get(url)
                        for request in driver.requests:
                            if request.response:
                                if request.url.startswith(cate['API'][sort][countryCode]):
                                    response = request.response
                                    body = str(zlib.decompress(response.body, 16+zlib.MAX_WBITS))
                                    break
                        driver.close()
                        try:
                            data = json.loads(body)
                            if sort == 'pop':
                                hasMore = data['data']['sections'][0]['has_more']
                            else:
                                hasMore = not data['nomore']
                            if hasMore == False:
                                stop = 1
                                break
                            if sort == "pop":
                                items = data['data']['sections'][0]['data']['item']
                                for item in items:
                                    shopids.add(item['shopid'])
                                page += 1
                            else:
                                items = data['items']
                                for item in items:
                                    shopids.add(item['shopid'])
                                page += 1
                        except:
                            stop = 1
                            break
        try:
            with open(os.path.join(outputDir, 'shopee', f'{countryCode}.txt'), "w+", newline= "") as f:
                    f.writelines(shopids)
        except:
            print(f"issue at write the file {countryCode}.txt")                   

         
def shopeeShopInsight(countryCode: str = "vie", stylebox_shopid: int = "", shopeeLink: str = "", saveLocal: bool = False, destination: str ="") -> dict:
    """
    This function to get the Shopee shop insight
    """
    countryCode = countryCode.upper()
    if len(countryCode) != 3:
        print("issue: The length of countryCode must be 3.")
        return None        
    else:
        items = []
        #Get scraper time
        now = datetime.strftime(datetime.now(), "%Y%m%d %H:%M:%S")
        
        # Get shop base
        if shopeeLink[-1] == "/":
            shopeeLink = shopeeLink[:len(shopeeLink)-1]
        userName = shopeeLink[shopeeLink.rfind("/")+1:]
        url = configs['SHOPEE']['SHOP']['BASE'][countryCode].format(userName)
        try:
            response = grequests.map([grequests.get(url)])
            data = response[0].json()['data']
            shopid = data["shopid"]
            # Get items
            url = configs['SHOPEE']['SHOP']['ALL_PRODUCTS'][countryCode].format(0,shopid)
            response = grequests.map([grequests.get(url)])
            totalItems = response[0].json()['total_count']
            urls = []
            limit = 100
            for offset in range(0,totalItems, limit): # (0,100,200...)
                url = configs['SHOPEE']['SHOP']['ALL_PRODUCTS'][countryCode].format(offset,shopid)
                urls.append(url)
            reqs = [grequests.get(u) for u in urls]
            responses = grequests.map(reqs)
            n = 1
            for response in responses:
                try:
                    data = response.json()['items']
                except:
                    break
                else:
                    for item in data:
                        itemid = item['itemid']
                        item['username'] = userName
                        item['date'] = datetime.strftime(datetime.now(),"%Y-%m-%d")
                        item['stylebox_shopid'] = stylebox_shopid
                        item['product_link'] = configs['SHOPEE']['ITEM']['URL'][countryCode].format(shopid,itemid)
                        item['reviews'] = []
                        url = configs['SHOPEE']['ITEM']['REVIEWS'][countryCode].format(itemid,0,shopid)
                        response = grequests.map([grequests.get(url)])
                        try:
                            data = response[0].json()['data']
                        except:
                            print("Can not access to url:", url)
                            break
                        else:
                            ratingTotal = data['item_rating_summary']['rating_total']
                            size = 60
                            urls = []
                            for offset in range(0, ratingTotal, size):
                                if offset <= 3000:
                                    url = configs['SHOPEE']['ITEM']['REVIEWS'][countryCode].format(itemid,offset,shopid)
                                    urls.append(url)
                            reqs = [grequests.get(url) for url in urls]
                            responses = grequests.map(reqs)
                            for response in responses:
                                try:
                                    ratings = response.json()['data']['ratings']
                                except:
                                    break
                                else:
                                    for rating in ratings:
                                        item['reviews'].append(rating)
                            items.append(item)
                            print(f"{userName}: Item {itemid} DONE. ({n}/{totalItems} products)")
                            n += 1                        
            if saveLocal == True:
                date = datetime.strftime(datetime.now(),'%Y-%m-%d')
                destination = os.path.join(outputDir,'shopee',f'{date}')
                if not os.path.exists(destination):
                    os.makedirs(destination)
                with open(os.path.join(destination, userName+".json"), "w+", encoding= "utf-8") as f:
                    json.dump(items, f, ensure_ascii= False, indent= 4)
        except Exception as e:
            print("issue in ShopeeInsight Method:", e)
    return items

def transformData(shop: json):
    pass

def main():
    begin= datetime.now()
    print("Begin:", begin)
    
    pairs = csvToDict(os.path.join(inputDir,'match-shops.csv'))
    spLinks = []
    lzdLinks = []
    date = datetime.strftime(datetime.now(), "%Y-%m-%d")
    for pair in pairs:
        spLinks.append((pair['stylebox_shopid'],pair['shopee_link']))
        lzdLinks.append((pair['stylebox_shopid'],pair['lazada_link']))

    bucketName = "3_dat_thailand"
    destination = bucketName + rf"/ecommerce-platform"
    for spLink in spLinks:
        items = shopeeShopInsight('th',spLink[0],spLink[1])
        usrName = items['username']
        try:
            print("Uploading data to Google Cloud Storage...")
            uploadGCP(data= items,dataType= "json", service= "bucket", destination= destination+f"/shopee/{date}/{usrName}.json")
            print(f'Shop: {usrName} DONE.')       
        except Exception as e:
            print(f'issue at shop {usrName}:', e) 
            continue

    finish = datetime.now()
    print("Finish:", finish)
    print("Duration:", finish - begin)


if __name__ == "__main__":
    # main()
    shopeeGetShops(['vie'])

    



    


