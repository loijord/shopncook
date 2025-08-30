#https://www.crummy.com/software/BeautifulSoup/bs4/doc/
#https://www.svidras.lt/barbora-prekiu-palyginimas/

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import requests.compat
import json
import re
import time
import pandas as pd
import os

#Kaip greičiau užkrauti puslapius per WebDriver:
#https://www.zenrows.com/blog/selenium-slow#block-resources-you-do-not-need
#https://stackoverflow.com/a/53481064

def initialize_driver(driver_path='chromedriver.exe'):
    '''Initialises WebDriver
    
    Requirements
    ------------
        * Download chromedriver.exe file from link: https://googlechromelabs.github.io/chrome-for-testing/#stable
        * Add it in location=driver_path
        
    Returns
    -------
        driver : selenium.webdriver.chrome.webdriver.WebDriver object
    '''
    # Selenium WebDriver nustatymai
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Naudojama grafinė sąsaja, kitu atveju rodomi ne visi svetainės elementai
    #Būtina pridėti, kitaip neveiks:
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3") 
    
    #Išjungiama daugybė opcijų, kad greičiau veiktų užkrovimas
    prefs = {'profile.default_content_setting_values': {'cookies': 2, 'images': 2, 'javascript': 2, 
             'plugins': 2, 'popups': 2, 'geolocation': 2, 
             'notifications': 2, 'auto_select_certificate': 2, 'fullscreen': 2, 
             'mouselock': 2, 'mixed_script': 2, 'media_stream': 2, 
             'media_stream_mic': 2, 'media_stream_camera': 2, 'protocol_handlers': 2, 
             'ppapi_broker': 2, 'automatic_downloads': 2, 'midi_sysex': 2, 
             'push_messaging': 2, 'ssl_cert_decisions': 2, 'metro_switch_to_desktop': 2, 
             'protected_media_identifier': 2, 'app_banner': 2, 'site_engagement': 2, 
             'durable_storage': 2}}

    chrome_options = Options()
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    #chrome_options.add_argument("start-maximized")
    chrome_options.add_argument("disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.experimental_options["prefs"] = prefs
    service = Service(driver_path)  # Chrome driver failo kelias/pavadinimas
    driver = webdriver.Chrome(service=service, options=chrome_options)  # Paleidžiamas WebDriver
    return driver

def fetch_and_parse(url, driver_path='chromedriver.exe'):
    '''Analyze url using Selenium and BeautifulSoup
    
    Parameters
    ----------
        url : string
    
    Returns
    -------
        soup : bs4.BeautifulSoup object
            
    Examples
    --------
    >>> soup = fetch_and_parse(r'https://barbora.lt/produktai/avieciu-uogiene-skanove-900-g')
    >>> out_string = soup.prettify()
    >>> with open(r'doctest_files/fetch_and_parse_test1.txt', 'r', encoding='utf-8') as f:
    ...     expected_string = f.read()
    >>> #check if expected output is similar to output of previous fetch
    >>> sum(x != y for x, y in zip(out_string, expected_string)) < 1000 
    True
    '''
    driver = initialize_driver(driver_path=driver_path)
    driver.get(url)  # Ikeliamas nurodytas URL su Selenium
    try:
        # Laukiama, kol bus įkeltas puslapio pagrindinis elementas
        WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    except TimeoutException:
        print(f"\n!!! Laiko limitas viršytas kraunant puslapį: {url} !!!")  # Laiko limito klaida
        return None
    soup = BeautifulSoup(driver.page_source, 'html.parser')  # Grąžinamas išanalizuotas puslapis
    driver.quit()
    return soup

def get_soup(url):
    driver = initialize_driver()
    soup = fetch_and_parse(url, driver)
    soup.prettify()
    return soup

#-----------------------------------------------------
def get_maxima_elements(url, driver_path='chromedriver.exe'):
    '''Returns dictionary that contains minimum elements needed for further data analysis
    
    Parameters
    ----------
        url : str
            Maxima e-shop site of the form 'https://barbora.lt/produktai/...'
    
    Examples
    --------
    >>> url = r'https://barbora.lt/produktai/avieciu-uogiene-skanove-900-g'
    >>> d = get_maxima_elements(url)
    >>> d.keys()
    dict_keys(['url', 'data_b_units', 'data_b_promotion', 'data_b_for_cart', 'valid_until', 'product_info'])
    '''
    try:
        soup = fetch_and_parse(url, driver_path=driver_path)
        product_div = soup.find("div", {"class": "b-product-info b-product--js-hook"})
        data_b_units = json.loads(product_div.get("data-b-units"))["units"][0]
        try:
            data_b_promotion = json.loads(product_div.get("data-b-promotion"))
        except Exception as e:
            data_b_promotion = None
        data_b_for_cart = json.loads(product_div.get("data-b-for-cart"))
        validity = [re.findall(r'validUntil\s*=\s*`([^`]+)`', str(text)) for text in soup.find_all('script')]
        valid_until_candidates = [n for n in validity if n]
        valid_until = valid_until_candidates[0][0] if valid_until_candidates else ''
        
        info = soup.find("dl", {"class": "b-dl-align-left b-product-info--info1"})
        product_info = dict()
        for dt in info.find_all('dt'):
            dd = dt.find_next_sibling('dd')
            if dd.text:
                product_info[dt.text.strip()] = dd.text
        
        d = dict(url = url,
                 data_b_units = data_b_units,
                 data_b_promotion = data_b_promotion,
                 data_b_for_cart = data_b_for_cart,
                 valid_until = valid_until,
                 product_info = product_info)
        return d
    except Exception as e: 
        print('MAXIMA parsing error (failed to fetch)', url)
        raise e

def get_maxima_data(d):
    '''Extract essential data from maxima elements
    >>> url = r'https://barbora.lt/produktai/avieciu-uogiene-skanove-900-g'
    >>> d = get_maxima_data(get_maxima_elements(url))
    >>> d.keys()
    dict_keys(['url', 'image', 'title', 'date', 'shop', 'price', 'comparative_unit', 'comparative_unit_price', 'discount', 'discount_price', 'comparative_unit_discount_price', 'weight', 'valid_until'])
    '''
    promotion = d['data_b_promotion']
    
    data = dict(url = d['url'],
                image = d['data_b_for_cart']['image'],
                title = d['data_b_for_cart']['title'],
                date = time.strftime("%Y-%m-%d"),
                shop = 'MAXIMA',
                price = d['data_b_units']['price'],
                comparative_unit = d['data_b_for_cart']['comparative_unit'].replace('.', ''),
                comparative_unit_price = d['data_b_for_cart']['comparative_unit_price'],
                discount = bool(promotion))

    if promotion:
        promotion_type = promotion['type']
        if promotion_type == 'X_FOR_Y':
            discount_price = round(promotion['price'] / promotion['quantity'], 2)
            price = data['price'] 
            comparative_unit_price = data['comparative_unit_price']
            data['discount_price'] = discount_price
            data['comparative_unit_discount_price'] = round(comparative_unit_price * discount_price / price, 2)
        elif promotion_type == 'CATEGORY_PERCENTAGE':
            price = promotion['oldPrice']
            comparative_unit_price = data['comparative_unit_price'] 
            k = 1 - promotion['percentage']/100
            data['discount_price'] = round(price * k, 2)
            data['comparative_unit_discount_price'] = round(comparative_unit_price * k, 2)
        elif promotion_type == 'LOYALTY_PRICE':
            price = promotion['oldPrice']
            discount_price = data['price']
            comparative_unit_discount_price = data['comparative_unit_price']
            k = discount_price / price
            data['price'] = price
            data['comparative_unit_price'] = round(comparative_unit_discount_price / k, 2)
            data['discount_price'] = discount_price
            data['comparative_unit_discount_price'] = comparative_unit_discount_price
        elif promotion_type == 'DISCOUNT_PRICE':
            price = promotion['oldPrice']
            discount_price = data['price']
            comparative_unit_price = promotion['oldComparativeRate']
            comparative_unit_discount_price = data['comparative_unit_price']
            data['price'] = price
            data['comparative_unit_price'] = comparative_unit_price
            data['discount_price'] = discount_price
            data['comparative_unit_discount_price'] = comparative_unit_discount_price
        #Note that LOYALTY_PRICE and DISCOUNT_PRICE are implemented in a different ways to support an easy fix option
        else:
            raise ValueError(f'promotion_type = {promotion_type} not implenented')
    else:
        data['discount_price'] = data['price']
        data['comparative_unit_discount_price'] = data['comparative_unit_price']

    if 'vnt' in data['comparative_unit']:
        if 'Grynasis kiekis (g/ml):' in d['product_info']:
            weight = int(d['product_info']['Grynasis kiekis (g/ml):']) / 1000
            data['comparative_unit'] = 'kg'
            data['comparative_unit_price'] = round(data['comparative_unit_price'] / weight, 2)
            data['comparative_unit_discount_price'] = round(data['comparative_unit_discount_price'] / weight, 2)
            data['weight'] = weight
    else:
        #Lazy to look in a parse elements...
        data['weight'] = round(data['price'] / data['comparative_unit_price'], 3)

    data['valid_until'] = d['valid_until']
    return data
    
    #debug promotion type if need:
    #data['promotion_type'] = promotion_type if promotion else None
#-----------------------------------------------------

def get_iki_elements(url):
    '''Returns dictionary that contains iki elements needed for further data analysis
    
    Parameters
    ----------
        url : str
            Iki e-shop site of the form 'https://www.lastmile.lt/chain/...'
    
    Examples
    --------
    >>> url = r'https://www.lastmile.lt/chain/PROMO-CashandCarry/product/Kiausiniai-L-dydis-rudi-fasuoti-10-vnt-3L10-U4D8D74'
    >>> d = get_iki_elements(url)
    >>> d.keys()
    dict_keys(['url', 'categoryId', 'chainId', 'constraintCode', 'conversionMeasure', 'countryOfOrigin', 'dateCreated', 'erpCode', '_id', 'id', 'lastMonthLowestPrice', 'maximumOrderQuantity', 'nutrition', 'photoUrl', 'productId', 'standardOrderQuantity', 'supplier', 'thumbUrl', 'unitOfMeasure', 'prc', 'isPromo', 'isInStock', 'isActive', 'isApproved', 'storeIds', 'slugs', 'name', 'description', 'allergens', 'storingConditions', 'ingredients', 'promoTags', 'hasNutritions', 'actualPrice', 'conversionValue', 'tags', 'costPrice', 'promo', 'depositPrice', 'dimensions', 'conversionToKg', 'unitWeight', 'isFixedWeight', 'manufacturerContact'])
    '''
    response = requests.get(url)

    # Check if response is good
    if response.status_code == 200:
        try:
            # Parse the response through bs4
            soup = BeautifulSoup(response.content, 'html.parser')    
            # Find the relevant object
            script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
            script_content = script_tag.string
            data = json.loads(script_content)
            # Retrieve all of the information
            product = data['props']['pageProps']['dehydratedState']['queries'][2]['state']['data'][0]['product']
            return {'url': url, **product}
        except Exception as e: 
            print('IKI parsing error (unknown)', url)
            raise e
    else:
        # Error handling
        print('IKI warning: (failed to fetch)', url)

def get_iki_data(d):
    '''Extract essential data from iki elements
    >>> url = r'https://www.lastmile.lt/chain/PROMO-CashandCarry/product/Kiausiniai-L-dydis-rudi-fasuoti-10-vnt-3L10-U4D8D74'
    >>> d = get_iki_data(get_iki_elements(url))
    >>> d.keys()
    dict_keys(['url', 'image', 'title', 'date', 'shop', 'price', 'comparative_unit', 'comparative_unit_price', 'discount', 'discount_price', 'comparative_unit_discount_price', 'weight', 'valid_until'])
    '''
    conversion = d['conversionValue']
    price = d['prc']['p']
    discount_price = d['prc']['lap']
    promo = d['promo']
    valid_until = d['prc']['lstill']
    if valid_until:
        match = re.search(r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\w+', valid_until).groupdict()
        valid_until = f"{match['year']}-{match['month']}-{match['day']}"
    else:
        valid_until = ''
    data = dict(url = d['url'],
                image = d['photoUrl'],
                title = d['name']['lt'],
                date = time.strftime("%Y-%m-%d"),
                shop = 'IKI',
                price = price,
                comparative_unit = d['conversionMeasure'].lower().replace('.', ''),
                comparative_unit_price = round(price / conversion, 2),
                discount = price != discount_price,
                discount_price = discount_price,
                comparative_unit_discount_price = round(discount_price / conversion, 2),
                weight = d['conversionToKg'],
                valid_until = valid_until)

    if promo:
        if promo['designation'] == 'quantity':
            k = promo['buyQuantity'] / (promo['buyQuantity'] + promo['getQuantity'])
            data['discount'] = True
            data['discount_price'] = round(data['discount_price'] * k, 2)
            data['comparative_unit_discount_price'] = round(discount_price / conversion * k, 2)
        else:
            raise ValueError(f'promo designation = {promo["designation"]} not implenented')

    return data
    
    #extra parameters not supported: 
    #d['lastMonthLowestPrice']
    #d['conversionToKg'] - prekės svoris kartu su pakuote
    #d['unitOfMeasure'] - matas, pagal kurį pirkėjas perka prekę (prekės vnt., kg arba l)
    #d['storeIds'] - kuriose parduotuvėse yra prekė
    #d['nutrition'] - maistinė sudėtis

    #conversionToKg might be wrong, check out to see:
    #https://www.lastmile.lt/chain/PROMO-CashandCarry/product/Avieciu-uogiene-VILROKA-12-kg-V26P818

#-----------------------------------------------------
def get_rimi_elements(url, driver_path='chromedriver.exe'):
    '''Returns dictionary that contains minimum elements needed for further data analysis
    
    Parameters
    ----------
        url : str
            Rimi e-shop site of the form 'https://www.rimi.lt/e-parduotuve/lt/produktai/...'
    
    Examples
    --------
    >>> url = r'https://www.rimi.lt/e-parduotuve/lt/produktai/mesa-ir-zuvis-/sviezia-paukstiena/vistiena/broileriu-file-gabaliukai-be-antibiotiku-500g/p/971720'
    >>> d = get_rimi_elements(url)
    >>> d.keys()
    dict_keys(['url', 'price_per', 'price_per_unit', 'old_price', 'valid_until', 'data'])
    '''
    response = requests.get(url)

    # Check if response is good
    if response.status_code == 200:
        try:
            soup = fetch_and_parse(url, driver_path=driver_path)
            price_per_string = soup.find("p", class_="price-per")
            if price_per_string is None:
                print('RIMI warning: (no price)', url)
                return None
            else:
                price_per = price_per_string.string.replace(" ", "").replace("\n", "")
            price_per_unit_element = soup.find("div", {'class': 'price-per-unit'})
            if price_per_unit_element:
                price_per_unit = price_per_unit_element.string.replace(" ", "").replace("\n", "")
            else:
                price_per_unit = None
            old_price_element = soup.find("p", class_="price__old-price")
        
            if old_price_element: 
                old_price = old_price_element.text.strip()
            else: 
                old_price = None
    
            data_element = soup.find("div", {'class': "cart-layout__main"}).find('script')
            data = json.loads(data_element.string, strict=False)
    
            valid_until = soup.find("p", class_="notice")
            if valid_until:
                valid_until = valid_until.text.strip()[-10:].replace('.', '-')
            else:
                valid_until = ''
    
            return dict(url = url,
                        price_per=price_per, 
                        price_per_unit=price_per_unit, 
                        old_price=old_price, 
                        valid_until=valid_until, 
                        data=data)
        except Exception as e: 
            print('Rimi parsing error (unknown)', url)
            raise e

    else:
        # Error handling
        print('RIMI warning: (failed to fetch)', url)
        return None

def get_rimi_data(d):
    '''Extract essential data from rimi elements
    >>> url = r'https://www.rimi.lt/e-parduotuve/lt/produktai/mesa-ir-zuvis-/sviezia-paukstiena/vistiena/broileriu-file-gabaliukai-be-antibiotiku-500g/p/971720'
    >>> d = get_rimi_data(get_rimi_elements(url))
    >>> d.keys()
    dict_keys(['url', 'image', 'title', 'date', 'shop', 'price', 'comparative_unit', 'comparative_unit_price', 'discount', 'discount_price', 'comparative_unit_discount_price', 'weight', 'valid_until'])
    '''
    data = dict(url = d['url'], image = d['data']['image'][0], 
                title = d['data']['name'], 
                date = time.strftime("%Y-%m-%d"),
                shop = 'RIMI',
                price = float(d['data']['offers']['price']),
                comparative_unit = None,
                comparative_unit_price = None,
                discount = False,
                discount_price = None,
                comparative_unit_discount_price = None,
                weight = None,
                valid_until = d['valid_until'])

    #Extract information from price of the form 12,34€/kg
    match = re.search(r'(?P<integer>\d+),(?P<fraction>\d+)€/(?P<unit>\w+)', d['price_per']).groupdict()
    
    data['discount_price'] = data['price']
    data['comparative_unit'] = match['unit']
    data['comparative_unit_price'] = float(match['integer'] + '.' + match['fraction'])
    data['comparative_unit_discount_price'] = data['comparative_unit_price']
    if match['unit'] in ['kg', 'l']:
        data['weight'] = round(data['price'] / data['comparative_unit_price'], 3)
    
    if d['price_per_unit']:
        data['discount'] = True
        match = re.search(r'(?P<integer>\d+),(?P<fraction>\d+)€/(?P<unit>\w+)', d['price_per_unit']).groupdict()
        data['comparative_unit_discount_price'] = float(match['integer'] + '.' + match['fraction'])
        data['discount_price'] = round(data['price'] * data['comparative_unit_discount_price'] / data['comparative_unit_price'], 2)

    if d['old_price']:
        data['discount'] = True
        match = re.search(r'(?P<integer>\d+),(?P<fraction>\d+)€', d['old_price']).groupdict()
        data['discount_price'] = data['price']
        data['comparative_unit_discount_price'] = data['comparative_unit_price']
        data['price'] = float(match['integer'] + '.' + match['fraction'])
        data['comparative_unit_price'] = round(data['comparative_unit_discount_price'] * data['price'] / data['discount_price'], 2)

    return data


def scrape(urls, offline=False, history_file='product_history.csv', update_history_file=True,
                 sorter={'by':['comparative_unit_discount_price', 'shop', 'discount'],
                               'ascending': [True, True, False]}):

    '''Extract essential data from multiple urls applying a proper method for each
    
    Parameters
    ----------
        offline : bool
            If True look for data in history file
            If False for each url find a method of scraping by a shop provided in url
        history_file : str
            Location of history file
        update_history_file : bool
        sorter : dict
            Parameters that sorts dataframe of products scraped (in df.sort_values design)
    
    Returns
    -------
        df : pd.DataFrame
            Dataframe of scraped urls 
            
    Examples
    --------
    >>> out_df = scrape([r'https://barbora.lt/produktai/avieciu-uogiene-skanove-900-g',
    ...                  r'https://www.lastmile.lt/chain/PROMO-CashandCarry/product/Kiausiniai-L-dydis-rudi-fasuoti-10-vnt-3L10-U4D8D74',
    ...                  r'https://www.rimi.lt/e-parduotuve/lt/produktai/mesa-ir-zuvis-/sviezia-paukstiena/vistiena/broileriu-file-gabaliukai-be-antibiotiku-500g/p/971720'])
    >>> expected_df = pd.read_csv(r'doctest_files/scrape_test1.csv')
    >>> cmp_values = ['url', 'image', 'title', 'shop', 'comparative_unit']
    >>> all(out_df[cmp_values].reset_index(drop=True) == expected_df[cmp_values])
    True
    >>> out_df.columns
    Index(['url', 'image', 'title', 'date', 'shop', 'price', 'comparative_unit',
           'comparative_unit_price', 'discount', 'discount_price',
           'comparative_unit_discount_price', 'weight', 'valid_until'],
          dtype='object')
    '''
    
    if offline:
        if history_file in os.listdir():
            history_df = pd.read_csv(history_file)
            idx = []
            for url in urls:
                bidx = history_df['url'] == url
                if bidx.any():
                    idx.append(bidx[::-1].idxmax())
            df = history_df.iloc[idx]
            if sorter:
                df = df.sort_values(**sorter)
        else:
            raise ValueError('Cant find history file')
        return df
    else:
        products = []
        for url in urls:
            try:
                if 'lastmile' in url:
                    products.append(get_iki_data(get_iki_elements(url)))            
                elif 'barbora' in url:
                    products.append(get_maxima_data(get_maxima_elements(url))) 
                elif 'rimi' in url:
                    products.append(get_rimi_data(get_rimi_elements(url)))
                else:
                    raise ValueError
            except Exception as e:
                print(f"Could not parse url: {url}")

        df = pd.DataFrame([product for product in products if product])
        if sorter:
            df = df.sort_values(**sorter)
        if update_history_file:
            if history_file in os.listdir():
                history_df = pd.read_csv(history_file)
                update_df = pd.concat([history_df, df]).drop_duplicates()
                update_df.to_csv(history_file, index=False, header=True)
            else:
                df.to_csv(history_file, index=False, header=True)
    return df

def get_view(df, sorter=None):
    '''Extract essential data from multiple urls applying a proper method for each
    
    Parameters
    ----------
        df : pd.DataFrame
            Dataframe that preserves format of products scraped in scrape method
        sorter : dict
            Parameters that sorts dataframe before displaying it (in df.sort_values design)
    
    Returns
    -------
        df_preview : pd.DataFrame
            Dataframe of displayable format
            
    Examples
    --------
    >>> df = scrape([r'https://barbora.lt/produktai/avieciu-uogiene-skanove-900-g',
    ...              r'https://www.lastmile.lt/chain/PROMO-CashandCarry/product/Kiausiniai-L-dydis-rudi-fasuoti-10-vnt-3L10-U4D8D74',
    ...              r'https://www.rimi.lt/e-parduotuve/lt/produktai/mesa-ir-zuvis-/sviezia-paukstiena/vistiena/broileriu-file-gabaliukai-be-antibiotiku-500g/p/971720'])
    >>> df_preview = get_view(df)
    >>> from IPython.display import Markdown, display
    >>> display(Markdown(get_view(out_df).to_markdown())) #doctest: +ELLIPSIS
    '''
    if sorter: 
        df = df.sort_values(**sorter)
    records = df.to_dict('records')
    new_records = []
    for item in records:
        d = {'shop': item['shop']}
        d['image'] = '<img src="' + item["image"] + '" width=100 height=60 />'
        d['title'] = f'<a href="{item['url']}"><table width="100"><td> {item['title']} </td></table></a>'
        
        if item['price'] == item['discount_price']:
            d['price'] = f'{item['price']}€'
        else:
            d['price'] = f"<div><strong>{item['discount_price']}€</strong></div><div><del>{item['price']}€</del></div>"

        unit = item['comparative_unit']
        if item['price'] == item['discount_price']:
            d['price_per'] = f'{item['comparative_unit_price']}€/{unit}'
        else:
            d['price_per'] = f"<div><strong>{item['comparative_unit_discount_price']}€/{unit}" +\
            f"</strong></div><div><del>{item['comparative_unit_price']}€/{unit}</del></div>"

        if item['price'] == item['discount_price']:
            d['off'] = ''
        else:
            d['off'] = f'-{round(100 * (item['price'] - item['discount_price']) / item['price'], 1)}%'

        d['weight'] = item['weight']
        d['date'] = item['date']
        d['valid_until'] = item['valid_until'] if item['valid_until']!='nan' else ''
        new_records.append(d)

    df_preview = pd.DataFrame(new_records)
    pd.set_option('styler.format.precision', 2)
    return df_preview

def balance_units(df):
    '''
    If comparative units are mixed between vnt and kg/l, convert all the vnt units to the most occurent weight unit
    comparative_unit_price and comparative_unit_discount_price values will be recalculated.
    Warns if there are unexpected units (not 'vnt', 'kg' or 'l').


    Parameters
    ----------
        df : pd.Dataframe
            Dataframe that contains: 
                'comparative_unit', 'comparative_unit_price', 'comparative_unit_discount_price', 'weight'
    
    Returns
    -------
        df : pd.DataFrame
            Antother dataframe with fixed columns
            
    Examples
    --------
    >>> out_df = scrape([r'https://barbora.lt/produktai/avieciu-uogiene-skanove-900-g',
    ...                  r'https://www.lastmile.lt/chain/PROMO-CashandCarry/product/Kiausiniai-L-dydis-rudi-fasuoti-10-vnt-3L10-U4D8D74',
    ...                  r'https://www.rimi.lt/e-parduotuve/lt/produktai/mesa-ir-zuvis-/sviezia-paukstiena/vistiena/broileriu-file-gabaliukai-be-antibiotiku-500g/p/971720'])
    
    >>> df = pd.DataFrame({'title': ['Smėlio formelės ledai', 'Ledai Baltija, 150 ml', 
    ...                              'Ledai CLEVER, 120 ml', 'Ledai BONBON MAGNUM su sūdyta karamele ir migdolais, 168 g'],
    ...                    'comparative_unit': ['vnt', 'l', 'l', 'kg'], 
    ...                    'comparative_unit_price': [2.49, 17.79, 1.58, 56.49],
    ...                    'comparative_unit_discount_price': [1.25, 8.40, 1.58, 56.49],
    ...                    'weight': [0.25, 0.15, 0.12, 0.168]})
    >>> expected_df = pd.DataFrame({'title': ['Smėlio formelės ledai', 'Ledai Baltija, 150 ml', 
    ...                             'Ledai CLEVER, 120 ml', 'Ledai BONBON MAGNUM su sūdyta karamele ir migdolais, 168 g'],
    ...                             'comparative_unit': ['l', 'l', 'l', 'kg'], 
    ...                             'comparative_unit_price': [9.96, 17.79, 1.58, 56.49],
    ...                             'comparative_unit_discount_price': [5.00, 8.40, 1.58, 56.49],
    ...                             'weight': [0.25, 0.15, 0.12, 0.168]})
    >>> all(expected_df == balance_units(df))
    True
    '''
    df = df.copy()
    vnt_idx = df['comparative_unit'] == 'vnt'
    weight_of_vnt = df.loc[vnt_idx, 'weight']
    
    if not df['comparative_unit'].isin(['vnt', 'kg', 'l']).all():
        bad_units_idx = ~df['comparative_unit'].isin(['vnt', 'kg', 'l'])
        print(f"Warning: unexpected units in item = {item}: {df.loc[bad_units_idx, 'comparative_unit']}")
        
    if vnt_idx.any() and not(vnt_idx.all()): 
        most_common_weight_unit = df.loc[df['comparative_unit'] != 'vnt', 'comparative_unit'].mode()[0]
        vnt_idx = df['comparative_unit'] == 'vnt'
        weight_of_vnt = df.loc[vnt_idx, 'weight']
        df.loc[vnt_idx, 'comparative_unit_price'] = df.loc[vnt_idx, 'comparative_unit_price'] / weight_of_vnt
        df.loc[vnt_idx, 'comparative_unit_discount_price'] = df.loc[vnt_idx, 'comparative_unit_discount_price'] / weight_of_vnt
        df.loc[vnt_idx, 'comparative_unit'] = most_common_weight_unit
    return df


if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)