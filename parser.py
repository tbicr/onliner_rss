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


_bad_pages_tokens = [
    ('К сожалению, в настоящий момент на сайте'.encode(),
     'самым жесточайшим образом проводятся ремонтные работы.'.encode(),
     'Нам страшно жаль, и мы приносим извинения за неудобства.'.encode()),
]


class BadPageException(Exception):
    pass


def _normalize_date(date):
    for rus, num in _dates.items():
        if rus in date:
            date = date.replace(rus, num)
            break
    return datetime.datetime.strptime(date, '%d %m %Y %H:%M')


def _expand_links(page_url, url):
    try:
        return urllib.parse.urljoin(page_url, url)
    except ValueError:
        return url


def parse_file(base, file):
    response = requests.get(urllib.parse.urljoin(base, file))
    return {
        'response': response.content,
        'content_type': response.headers.get('Content-Type'),
    }


def parse_icon(base):
    return parse_file(base, '/pic/favicon.ico')


def _get_page_or_raise(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise BadPageException('Cannot fetch page {} (status code {})'.format(url, response.status_code))
    content = response.content
    for tokens in _bad_pages_tokens:
        if all(token in content for token in tokens):
            raise BadPageException('Bad page content for page {}'.format(url))
    return content


def parse_topic(base, base_page_url, max_items):
    if not urllib.parse.urlparse(base_page_url).netloc:
        base_page_url = urllib.parse.urljoin(base, base_page_url)
    content = _get_page_or_raise(base_page_url)
    base_page = lxml.html.fromstring(content)
    try:
        page_url = base_page.cssselect('.pages-fastnav li:not(.page-next) a')[-1].attrib['href']
    except IndexError:
        page_url = base_page_url
    messages = []
    max_pages = max_items // 20 + 1
    while max_pages >= 0:
        page_url = urllib.parse.urljoin(base_page_url, page_url)
        content = _get_page_or_raise(page_url)
        page = lxml.html.fromstring(content)
        for node in page.xpath('//*[@src]'):
            url = node.get('src')
            url = _expand_links(page_url, url)
            node.set('src', url)
        for node in page.xpath('//*[@href]'):
            href = node.get('href')
            href = _expand_links(page_url, href)
            node.set('href', href)
        title = page.cssselect('h1')[0].text_content()
        for item in reversed(page.cssselect('.b-messages-thread li.msgpost:not(.msgfirst)')):
            message = {}
            message['id'] = item.cssselect('.b-msgpost-txt small a')[0].attrib['href']
            message['url'] = message['id']
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
