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
    author_id = Column(Integer)
    belong_id = Column(Integer)


class ZHColumn(Base):
    __tablename__ = 'core_zhcolumn'

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime)
    modify_time = Column(DateTime)
    name = Column(String)
    link = Column(String)
    hash = Column(String, unique=True)
    slug = Column(String, unique=True)
    description = Column(String, nullable=True)
    avatar = Column(String)
    creator_id = Column(Integer, nullable=True)


class ZHUser(Base):
    __tablename__ = 'core_zhuser'

    id = Column(Integer, primary_key=True)
    zuid = Column(String)
    create_time = Column(DateTime)
    modify_time = Column(DateTime)
    name = Column(String)
    link = Column(String)
    hash = Column(String, unique=True)
    slug = Column(String, unique=True)
    description = Column(String, nullable=True)
    headline = Column(String, nullable=True)
    avatar = Column(String)
    crawl_column = Column(Boolean, default=False)
    crawl_follow = Column(Boolean, default=False)


class Tag(Base):
    __tablename__ = 'core_tag'

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime)
    modify_time = Column(DateTime)
    name = Column(String)


class ZHArticleTagRef(Base):
    __tablename__ = 'core_zharticle_tags'
    id = Column(Integer, primary_key=True)
    zharticle_id = Column(Integer)
    tag_id = Column(Integer)


class ZHRandomColumn(Base):
    __tablename__ = 'core_zhrandomcolumn'

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime)
    modify_time = Column(DateTime)
    slug = Column(String, unique=True)
    link = Column(String)
    hash = Column(String, unique=True)


engine = create_engine('postgresql+psycopg2://postgres:123456qq@localhost:5432/lighthouse',
                       encoding='utf-8'.encode())

DBSession = sessionmaker(bind=engine)
