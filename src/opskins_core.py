# -*- coding: utf-8 -*-
import time
import random
import selenium.webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import http.cookiejar
import requests
from lxml import html
import config as mc

instance = None


class Opskins_Market(mc.MetaConfig):

    def __init__(self, *args):
        super().__init__()

        if len(args) != 0:
            for item in args[0]:
                setattr(self, item, args[0][item])
        else:
            return

        # wait_time = ajax_wait_base+0.01*random.randint(0, ajax_wait_random)

        self.shop_url = "https://opskins.com/?loc=shop_browse"
        self.shop_prefix = u"https://opskins.com/"
        self.ajax_url = "https://opskins.com/ajax/browse_scroll.php" \
                   "?page=%d&appId=730&contextId=2"
        self.loaded_xpath = '//*[@id="modalContainer"]'
        self.wear_keys = {
            'Minimal Wear': u'MW',
            'Field-Tested': u'FT',
            'Well-Worn': u'WW',
            'Factory New': u'FN',
            'Battle-Scarred': u'BS'
        }

        self.initUI()

    def initUI(self):
        output_file_name = "opskins_data.csv"
        results = self.parse_opskins()
        self.save_items(output_file_name, results)


    def wear_key(self, input):
        if not input:
            return [u""]
        text = input[0].strip()
        if not (text in self.wear_keys):
            return input
        return [self.wear_keys[text]]


    def strip_wear_text(self, input):
        if not input:
            return [u""]
        text = input[0].strip()
        return [text.replace(u'Wear: ', u'')]


    def calculate_discount(self, price, suggested_price):
        p = float(price[0].replace(u'$', u'').replace(u',', u'').strip())
        try:
            if suggested_price[0] == u'No Market Price':
                return [""]
            else:
                sp = float(suggested_price[0].replace(u'$', u'').strip())
        except ValueError:
            return [""]
        discount = (sp - p) / sp
        discount_prc = round(discount * 100)
        if discount_prc <= 0:
            return [""]
        return [u"%d%% OFF" % discount_prc]


    def convert_price(self, price_value_list):
        #except non price values like 'High Grade Key', '99.000.00' etc
        try:
            price = price_value_list[0].replace(u'$', u'').strip().replace(',', '')
        except:
            price = '0.0'
        return price


    def parse_output(self, data):
        tree = html.fromstring(data)
        divs = tree.xpath("//div[contains(@class, 'featured-item')]")
        results = list()
        for record in divs:
            name = record.xpath('.//a[@class="market-name market-link"]/text()')
            href = record.xpath('.//a[@class="market-name market-link"]/@href')
            name2 = record.xpath('.//div[@class="item-desc"]/'
                                 'small[contains(@style, "color")]/text()')
            price = record.xpath('.//div[@class="item-amount"]/text()')
            quality = record.xpath('.//div[@class="item-desc"]'
                                   '/small[@class="text-muted"]/text()')
            wear_value = record.xpath('.//div[contains(@class, "wear-value")]'
                                      '/small[@class="text-muted"]/text()')
            suggested_price = record.xpath('.//span[@class="suggested-price"]'
                                           '/text()')

            # format scraped data
            discount = self.calculate_discount(price, suggested_price)
            quality_formatted = self.wear_key(quality)
            wear_value_formatted = self.strip_wear_text(wear_value)
            price = self.convert_price(price)

            opskins_comission = int(self.comission)/100
            opskins_fixed_price = self.evaluate_opskins_price(price, opskins_comission, self.exchange_rate)
            price_list_transit = [str(opskins_fixed_price)]

            full_record_fixed = [href, name, name2, price_list_transit,
                           quality_formatted, wear_value_formatted,
                           discount]

            flat_list = list()
            for sublist in full_record_fixed:
                if sublist:
                    flat_list.append(sublist[0].strip())
                else:
                    flat_list.append(u"")
            results.append(flat_list)
        return results

    # parse items from opskins market
    def parse_opskins(self):
        # try to use chrome
        try:
            driver = selenium.webdriver.Chrome()
        # if not, then use mozilla
        except:
            # ypu may use
            # executable_path constructor variable
            driver = selenium.webdriver.Firefox(executable_path='C:\LIBS_ETC\BROWSER_DRIVERS\geckodriver.exe')

        driver.get(self.shop_url)

        # 120 - empiric correctly value
        wait = WebDriverWait(driver, 120)
        wait.until(EC.presence_of_element_located((By.XPATH, self.loaded_xpath)))
        cookies = driver.get_cookies()
        user_agent = driver.execute_script("return navigator.userAgent;")
        xcsrf = ' '
        b = http.cookiejar.CookieJar()

        # edit cookies for correct work with ajax form
        for i in cookies:
            if i['name'] == 'opskins_csrf_token':
                xcsrf = i['value']
            if 'expiry' in i:
                expire_value = i['expiry']
            else:
                expire_value = None

            ck = http.cookiejar.Cookie(
                name=i['name'], value=i['value'], domain=i['domain'],
                path=i['path'], secure=i['secure'], rest=False, version=0,
                port=None, port_specified=False, domain_specified=False,
                domain_initial_dot=False, path_specified=True,
                expires=expire_value, discard=True, comment=None,
                comment_url=None, rfc2109=False
            )

            # set edited cookies
            b.set_cookie(ck)

        # create header
        h = {
            'User-Agent': user_agent,
            'referer': 'https://opskins.com/?loc=shop_browse',
            'x-csrf': xcsrf,
            'x-op-userid': '0',
            'x-requested-with': 'XMLHttpRequest',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.8'
        }

        results = list()
        page_index = 1

        while len(results) < self.record_count:
            r = requests.get(self.ajax_url % page_index, cookies=b, headers=h)
            r.encoding = 'utf-8'
            page_index += 1
            results = results + self.parse_output(r.text)
            
            # go to the next page or not
            if (len(results) > self.record_count):
                break

            # add some "stochastic"
            wait_time = self.mint + 0.01 * random.randint(0, self.maxt)
            time.sleep(wait_time)
        driver.close()
        return results


    # dump data into file
    def save_items(self, file_name, data):
        f = open(file_name, 'wb')
        header = u"index,URL,c_market_name_en,c_market_name_origin," \
                 u"c_price,c_quality,c_float,discount\n"
        f.write(header.encode('utf-8'))
        index = 0
        for record in data:
            text = [str(index), u',', self.shop_prefix]
            for l in ([x,u','] for x in record):
                text.extend(l)
            index += 1
            f.write(''.join(text).replace(u'\n', u'')
                    .replace(u'\r', u'').encode('utf-8'))
            f.write(u'\n'.encode('utf-8'))
        f.close()