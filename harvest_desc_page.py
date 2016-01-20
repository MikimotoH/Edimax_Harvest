#!/usr/bin/env python3
# -*- coding: utf-8 -*-
unicodedot1 ='‧'
unicodedot2='•'
unicodedot =unicodedot1+unicodedot2
from pyquery import PyQuery as pq
from lxml import etree
import html2text
import re
from urllib import parse
import sqlite3
from my_utils import uprint,ulog
from datetime import datetime
import pdb


conn=None
def sql(query:str, var=None):
    global conn
    csr=conn.cursor()
    try:
        if var:
            rows = csr.execute(query,var)
        else:
            rows = csr.execute(query)
        if not query.startswith('SELECT'):
            conn.commit()
        if query.startswith('SELECT'):
            return rows.fetchall()
        else:
            return
    except sqlite3.Error as ex:
        print(ex)
        raise ex

def html2md(d, css):
    html= etree.tostring(d(css)[0]).decode('utf-8')
    h = html2text.HTML2Text()
    h.body_width=0
    h.ignore_links=True
    h.ignore_emphasis=True
    h.ignore_images=True
    return h.handle(html)

def scrape_desc(product_page):
    d = pq(url=product_page)
    image_url=d('.block01 > div:nth-child(2) > table:nth-child(2) > tr > td > table:nth-child(2) > tr > td > table > tr > td > a > img')[0].attrib['src']
    if not re.match(r'http:|https:', image_url):
        image_url = parse.urljoin(product_page, image_url)
    md = html2md(d, '.font-blue02')
    it = iter(md.splitlines())
    for l in it:
        if ' | ' not in l:
            continue
        field_name,_,field_value = l.partition(' | ')
        field_name = field_name.strip(' :|'+unicodedot)
        field_value=field_value.strip()
        if not field_value:
            while True:
                try:
                    l = next(it).strip('* -\n'+unicodedot)
                    if not l:
                        continue
                    field_value += (l+'\n')
                except StopIteration:
                    break
            field_value = field_value.strip()
            assert field_value
        #print('field_name="%s"'%field_name)
        #print('field_value="%s"'%field_value)
        if field_name=='Model Number':
            model = field_value
        elif field_name=='Product Name':
            prod_name = field_value
        elif field_name=='Product Line':
            prod_line = field_value
        elif field_name=='Description':
            desc = field_value
    fw_ver,fw_desc,fw_date,fw_url= [None]*4
    try:
        fw_tab_text = d('.block01 > div:nth-child(2) > table:nth-child(2) > tr > td > table:nth-child(4) > tr > td:nth-child(2)')[0].text_content().strip()
        if fw_tab_text != 'Firmware':
            raise IndexError()

        fw_row = d('.block01 > div:nth-child(2) > table:nth-child(2) > tr > td > table:nth-child(5) > tr:nth-child(2)')[0]
        fw_ver, fw_desc, fw_date, fw_url, *residual = fw_row.cssselect('td')
        fw_ver = fw_ver.text_content().strip()
        fw_desc = fw_desc.text_content().strip()
        fw_date = fw_date.text_content().strip()
        fw_date = datetime.strptime(fw_date, '%Y-%m-%d')
        fw_url = fw_url.cssselect('a')[0].attrib['href']
        fw_url = parse.urljoin(d.base_url, fw_url)
        uprint('fw_url= %s'%fw_url)

        # html = etree.tostring(fw_row).decode('utf8')
        # html = re.sub(r'<tr.*?>|</tr>|<td.*?>|</td>|<p>|</p>|<img.*?>|<table.*?>|</table>|\t|\n', '', html).strip()
        # fw_url= re.search(r'<a .*href="(.+?)"', html).group(1)
        # if not re.match('http:|https:', fw_url):
        #     fw_url = parse.urljoin(d.base_url, fw_url)
        # fw_ver, fw_desc, fw_date = [_ for _ in html.split('  ') if _]
        # fw_date = re.search(r'\d{4}-\d{2}-\d{2}', fw_date).group(0)
        # datetime.strptime(fw_date,'%Y-%m-%d')

    except IndexError:
        pass
    except Exception as ex:
        print(ex)
        pdb.set_trace()
        
    sql("insert or replace into TFiles (model,prod_name,product_page,image_url,desc,prod_line, fw_ver, fw_desc, fw_date, fw_url) VALUES (:model,:prod_name,:product_page,:image_url,:desc,:prod_line,:fw_ver,:fw_desc,:fw_date,:fw_url)", locals())
    uprint('UPSERT "%(model)s","%(prod_name)s", "%(fw_ver)s", "%(fw_date)s" '%locals())

def modelWalker():
    d = pq(url='http://www.edimax.com.tw/en/support_download.php?pl1_id=1')
    rows = d('.block01 > div:nth-child(2) > table:nth-child(2) > tr > td > table:nth-child(2) > tr')
    for irow, row in enumerate(rows):
        try:
            tds = [_.text_content().strip() for _ in row.cssselect('td') if _.text_content().strip()]
            uprint('tds=%s'%tds)
            link = row.cssselect('a')[0]
            product_page = parse.urljoin(d.base_url, link.attrib['href'])
            scrape_desc(product_page)
        except IndexError:
            continue

def main():
    global conn
    conn=sqlite3.connect('Edimax.sqlite3')
    sql("CREATE TABLE IF NOT EXISTS TFiles("
        "id INTEGER NOT NULL,"
        "model TEXT," 
        "prod_name TEXT," 
        "product_page TEXT," 
        "image_url TEXT," 
        "desc      TEXT," 
        "prod_line TEXT," 
        "fw_ver  TEXT," 
        "fw_desc TEXT," 
        "fw_date DATE," 
        "fw_url  TEXT," 
        "fw_sha1  TEXT," 
        "PRIMARY KEY (id),"
        "UNIQUE(model)"
        ")")
    modelWalker()
    # scrape_desc('http://www.edimax.com.tw/en/support_detail.php?pd_id=346&pl1_id=3&pl2_id=18')
    conn.close()


if __name__=='__main__':
    main()
