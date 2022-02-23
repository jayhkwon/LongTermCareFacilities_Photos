"""
국민건강보험공단 장기요양기관 사진첩 크롤링

Author: Jay Hyoung-Keun Kwon
Date: February 23, 2022
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

import pandas as pd
import numpy as np
import time
import geckodriver_autoinstaller
import re
import requests

"""
For a given facility, retrieve the url links of all photos

Input
@driver: webdriver(selenium)
@tbl: pandas dataframe
@h: integer

Return: Python dictionary of images
"""

def get_images(driver, tbl, h):
    images = {}
    pages = driver.find_elements(By.XPATH, '//a[@class = "link_page"]')
    
    #length of pages is one less than the actual number of pages
    num_pages = len(pages)
    
    p1 = re.compile(r"'([0-9]*)',")
    p2 = re.compile(r",'([A-Z0-9]*)',")
    p3 = re.compile(r",'([a-z0-9]*)'\);$")
    for p in range(num_pages+1):
        img_lst = driver.find_elements(By.XPATH, '//div[@class = "img_wrap"]')
        for i in range(len(img_lst)):
            img_e = img_lst[i].find_elements(By.TAG_NAME, 'a')
            if len(img_e) > 0:
                ind = p*12 + i
                img_nm = img_lst[i].find_elements(By.TAG_NAME, 'img')[0].get_attribute('alt').strip()
                img_e2 = img_e[0].get_attribute('onclick')

                if len(img_e2) > 0:
                    blbdId = p1.findall(img_e2)[0]
                    artiId = p2.findall(img_e2)[0]
                    pgmId = p3.findall(img_e2)[0]
                    url = f"https://www.longtermcare.or.kr/npbs/r/a/104/selectBlbdArtiDtl.web?ltcAdminSym={tbl.sym[h]}&blbdId={blbdId}&artiId={artiId}&pgmId={pgmId}"

                    response = requests.get(url)
                    if response.status_code == 200:
                        html = response.text
                        soup = BeautifulSoup(html, 'html.parser')
                        photo = soup.select_one('#blbd_arti_vo > div > div.tbl.tbl_row.tbl_point > table > tbody > tr:nth-of-type(3) > td > div > p > span.tbl_file.f_l > a')
                        if photo != None:
                            images[ind] = [img_nm, 'https://www.longtermcare.or.kr' + photo['href']]
                    else:
                        print(response.status_code)

        if (num_pages > 0) & (p!= num_pages):
            pages = driver.find_elements(By.XPATH, '//a[@class = "link_page"]')
            pages[p].click()
    return images

if __name__ == '__main__':
    """
    장기요양시설 일반현황조회 자료
    Source: https://www.data.go.kr/data/15058856/openapi.do
    API request: http://apis.data.go.kr/B550928/getLtcInsttDetailInfoService01/getGeneralSttusDetailInfoItem01
    
    Variables: 
    @'adminNm': 장기요양기관이름
    @'longTermAdminSym': 장기요양기관기호
    @'longTermPeribRgtDt': 장기요양기관지정일
    @'siDoCd': 시도코드
    @'siGunGuCd': 시군구코드
    @'stpRptDt': 설치신고일자
    """
    hosp = pd.read_csv('longTermCareFacilities.csv')[['adminNm', 'longTermAdminSym', 'longTermPeribRgtDt', 'siDoCd', 'siGunGuCd', 'stpRptDt']]
    hosp.columns = ['name', 'sym', 'certified_at', 'siDoCd', 'siGunGuCd', 'registered']
    hosp['link'] = hosp['sym'].apply(lambda x: 'https://www.longtermcare.or.kr/npbs/r/a/201/selectBlbdArtiList?ltcAdminSym='+str(x))
    hosp_f = hosp.drop_duplicates(subset = ['name', 'sym', 'link'], keep = 'first').copy().reset_index(drop = True)
    
    num_hosp = hosp_f.shape[0]
    geckodriver_autoinstaller.install()
    driver = webdriver.Firefox()
    image, df_img = {}, {}
    
    start = time.time()
    for h in range(num_hosp-1):
        driver.get(hosp_f.link[h])
        image[hosp_f.sym[h]] = get_images(driver, hosp_f, h)
        
        #marking progress
        print('.', end = '')
        if (h!= 0) & (h % 100 == 0):
            print(f'{round(h/100, 0)}')
        if (h!=0) & (h%1000 == 0):
            t = pd.DataFrame([(i, k+1, l[0], l[1]) for i, j in image.items() for k, l in j.items()],
                            columns = ['sym', 'photo_num', 'photo_name', 'photo_link'])
            #Can save intermediate files as well
            #t.to_csv(f'photos_{h-1000}-{h}.csv', index = False, encoding = 'utf-8-sig')
            df_img[(h-1000)/1000] = t
    end = time.time()
    print(f'Total process took {round((end-start)/3600,0)} hours {round(((end-start)%3600)/60,0)} minutes and {round((end-start)%60,0)} seconds')
    driver.close()

    #gather all
    df = pd.concat(df_img, ignore_index = True)
    df.to_csv('longTermCareFacilities_Photos.csv', index = False, encoding = 'utf-8-sig')