# coding: utf-8

from __future__ import unicode_literals

import requests

headers = {
    'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/535.20 (KHTML, like Gecko) Chrome/19.0.1036.7 Safari/535.20",
}

url = 'https://zhuanlan.zhihu.com/p/27152885'
url = 'https://zhuanlan.zhihu.com/api/columns/canzhuoqitan'

resp = requests.get(url, headers=headers)

print resp.content
# import json
# import re
# m = re.findall(r'<textarea id="preloadedState" hidden>(.*?)</textarea>', resp.content)
# # print json.loads(m[0])
# print m[0]
# print json.dumps({'a': 1})
#
# a = '2017-05-28T15:26:22+08:00'
#
# import datetime
#
# b = datetime.datetime.strptime(a, '%Y-%m-%dT%H:%M:%S+08:00')
#
# print b