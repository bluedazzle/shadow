# coding: utf-8
from __future__ import unicode_literals

import sys
import os
import logging
from Shadow.settings import BASE_DIR, USER_AGENTS

PRO_PATH = '{0}/{1}'.format(BASE_DIR, 'shadow')
sys.path.append(PRO_PATH)
os.environ['SCRAPY_PROJECT'] = PRO_PATH

from Shadow.spiders.zhihu_spider import ZHPeopleFollowsSpider
from scrapy.crawler import CrawlerProcess
from scrapy.conf import settings

settings.overrides.update({'USER_AGENTS': USER_AGENTS})
count = 1
while 1:
    logging.info('start crawl zh people by {0} times'.format(count))
    process = CrawlerProcess(settings)
    process.crawl(ZHPeopleFollowsSpider)
    process.start()
