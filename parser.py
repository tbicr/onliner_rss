import datetime
import urllib.parse

import lxml.etree
import lxml.html
import requests


def parse_icon():
    return requests.get('http://content.onliner.by/pic/favicon.ico').content


def parse_topic(base_page_url, max_items):
    base_page = lxml.html.fromstring(requests.get(base_page_url).content)
    try:
        page_url = base_page.cssselect('.pages-fastnav li:not(.page-next) a')[-1].attrib['href']
    except IndexError:
        page_url = base_page_url
    messages = []
    max_pages = max_items // 20 + 1
    while max_pages >= 0:
        page = lxml.html.fromstring(requests.get(urllib.parse.urljoin(base_page_url, page_url)).content)
        title = page.cssselect('h1')[0].text_content()
        for item in reversed(page.cssselect('.b-messages-thread li.msgpost:not(.msgfirst)')):
            message = {}
            message['id'] = item.cssselect('.b-msgpost-txt small a')[0].attrib['href']
            message['url'] = urllib.parse.urljoin(base_page_url, page_url) + message['id']
            message['author'] = item.cssselect('.b-mtauthor-i>.mtauthor-nickname a')[0].text_content()
            message['title'] = title
            message['content'] = lxml.etree.tostring(item.cssselect('.content')[0],
                                                     pretty_print=True, method='html').decode()
            message['updated'] = datetime.datetime.utcnow()
            message['published'] = datetime.datetime.utcnow()
            messages.append(message)
            if len(messages) >= max_items:
                break
        try:
            page_url = page.cssselect('.pages-fastnav li.page-prev a')[0].attrib['href']
        except IndexError:
            break
        max_pages -= 1
    return title, reversed(messages)
