import datetime
import urllib.parse

import lxml.etree
import lxml.html
import requests


_dates = {
    'января': '01',
    'февраля': '02',
    'марта': '03',
    'апреля': '04',
    'мая': '05',
    'июня': '06',
    'июля': '07',
    'августа': '08',
    'сентября': '09',
    'октября': '10',
    'ноября': '11',
    'декабря': '12',
}


def _normalize_date(date):
    for rus, num in _dates.items():
        if rus in date:
            date = date.replace(rus, num)
            break
    return datetime.datetime.strptime(date, '%d %m %Y %H:%M')


def parse_file(base, file):
    response = requests.get(urllib.parse.urljoin(base, file))
    return {
        'response': response.content,
        'content_type': response.headers.get('Content-Type'),
    }


def parse_icon(base):
    return parse_file(base, '/pic/favicon.ico')


def parse_topic(base, base_page_url, max_items):
    if not urllib.parse.urlparse(base_page_url).netloc:
        base_page_url = urllib.parse.urljoin(base, base_page_url)
    base_page = lxml.html.fromstring(requests.get(base_page_url).content)
    try:
        page_url = base_page.cssselect('.pages-fastnav li:not(.page-next) a')[-1].attrib['href']
    except IndexError:
        page_url = base_page_url
    messages = []
    max_pages = max_items // 20 + 1
    while max_pages >= 0:
        page = lxml.html.fromstring(requests.get(urllib.parse.urljoin(base_page_url, page_url)).content)
        for node in page.xpath('//*[@src]'):
            url = node.get('src')
            url = urllib.parse.urljoin(base_page_url, url)
            node.set('src', url)
        for node in page.xpath('//*[@href]'):
            href = node.get('href')
            href = urllib.parse.urljoin(base_page_url, href)
            node.set('href', href)
        title = page.cssselect('h1')[0].text_content()
        for item in reversed(page.cssselect('.b-messages-thread li.msgpost:not(.msgfirst)')):
            message = {}
            message['id'] = item.cssselect('.b-msgpost-txt small a')[0].attrib['href']
            message['url'] = urllib.parse.urljoin(base_page_url, page_url) + message['id']
            message['author'] = item.cssselect('.b-mtauthor-i>.mtauthor-nickname a')[0].text_content()
            message['title'] = title
            message['content'] = lxml.etree.tostring(item.cssselect('.content')[0],
                                                     pretty_print=True, method='html').decode()
            message['published'] = _normalize_date(item.cssselect('.msgpost-date span')[0].text_content())
            message['updated'] = message['published']
            messages.append(message)
            if len(messages) >= max_items:
                break
        try:
            page_url = page.cssselect('.pages-fastnav li.page-prev a')[0].attrib['href']
        except IndexError:
            break
        max_pages -= 1
    return title, reversed(messages)
