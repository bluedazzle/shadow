# coding: utf-8
from __future__ import unicode_literals
from __future__ import absolute_import

import sys
import os
import logging
from settings import BASE_DIR, USER_AGENTS

# PRO_PATH = '{0}/{1}'.format(BASE_DIR, 'shadow')
sys.path.append(BASE_DIR)
os.environ['SCRAPY_PROJECT'] = BASE_DIR

from Shadow.spiders.zhihu_spider import ZHPeopleColumnSpider
from scrapy.conf import settings
from twisted.internet import reactor
from scrapy.crawler import CrawlerRunner

settings.overrides.update({'USER_AGENTS': USER_AGENTS})
count = 1
while 1:
    logging.info('start crawl people column by {0} times'.format(count))
    process = CrawlerRunner(settings)
    d = process.crawl(ZHPeopleColumnSpider)
    d.addBoth(lambda _: reactor.stop())
    reactor.run()
