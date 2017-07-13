# coding: utf-8

from __future__ import unicode_literals
from models import DBSession, ZHArticle
from sqlalchemy import func

session = DBSession()
print session.query(func.count(ZHArticle.id)).scalar()