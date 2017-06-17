# coding: utf-8

from __future__ import unicode_literals

from sqlalchemy import Column, String, DateTime, Integer, Boolean, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Proxy(Base):
    __tablename__ = 'core_proxy'

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime)
    modify_time = Column(DateTime)
    host = Column(String)
    port = Column(Integer)
    protocol = Column(Integer)
    available = Column(Boolean)


class ZHArticle(Base):
    __tablename__ = 'core_zharticle'

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime)
    modify_time = Column(DateTime)
    title = Column(String)
    md5 = Column(String, unique=True)
    content = Column(String)
    summary = Column(String)
    cover = Column(String)
    link = Column(String)
    token = Column(String)


engine = create_engine('mysql+pymysql://root:123456qq@localhost:3306/lighthouse?charset=utf8', encoding='utf-8'.encode())

DBSession = sessionmaker(bind=engine)
