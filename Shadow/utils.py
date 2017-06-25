# coding: utf-8
from __future__ import unicode_literals

import hashlib


def md5(string):
    return hashlib.md5(string).hexdigest()