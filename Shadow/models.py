# coding: utf-8

from __future__ import unicode_literals

from sqlalchemy import Column, String, DateTime, Integer, Boolean, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def _unique(session, cls, hashfunc, queryfunc, constructor, arg, kw):
    new = False
    cache = getattr(session, '_unique_cache', None)
    if cache is None:
        session._unique_cache = cache = {}

    key = (cls, hashfunc(*arg, **kw))
    if key in cache:
        return cache[key], new
    else:
        with session.no_autoflush:
            q = session.query(cls)
            q = queryfunc(q, *arg, **kw)
            obj = q.first()
            if not obj:
                new = True
                obj = constructor(*arg, **kw)
                session.merge(obj)
        cache[key] = obj
        return obj, new


class UniqueMixin(object):
    @classmethod
    def unique_hash(cls, *arg, **kw):
        raise NotImplementedError()

    @classmethod
    def unique_filter(cls, query, *arg, **kw):
        raise NotImplementedError()

    @classmethod
    def as_unique(cls, session, *arg, **kw):
        return _unique(
            session,
            cls,
            cls.unique_hash,
            cls.unique_filter,
            cls,
            arg, kw
        )


class Proxy(Base):
    __tablename__ = 'core_proxy'

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime)
    modify_time = Column(DateTime)
    host = Column(String)
    port = Column(Integer)
    protocol = Column(Integer)
    available = Column(Boolean)


class ZHArticle(UniqueMixin, Base):
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

    @classmethod
    def unique_hash(cls, *args, **kwargs):
        return kwargs['md5']

    @classmethod
    def unique_filter(cls, query, *args, **kwargs):
        return query.filter(ZHArticle.md5 == kwargs['md5'])


class ZHColumn(UniqueMixin, Base):
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

    @classmethod
    def unique_hash(cls, *args, **kwargs):
        return kwargs['hash']

    @classmethod
    def unique_filter(cls, query, *args, **kwargs):
        return query.filter(ZHColumn.hash == kwargs['hash'])


class ZHUser(UniqueMixin, Base):
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

    @classmethod
    def unique_hash(cls, *args, **kwargs):
        return kwargs['slug']

    @classmethod
    def unique_filter(cls, query, *args, **kwargs):
        return query.filter(ZHUser.slug == kwargs['slug'])


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


class ZHRandomColumn(UniqueMixin, Base):
    __tablename__ = 'core_zhrandomcolumn'

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime)
    modify_time = Column(DateTime)
    slug = Column(String, unique=True)
    link = Column(String)
    hash = Column(String, unique=True)

    @classmethod
    def unique_hash(cls, *args, **kwargs):
        return kwargs['slug']

    @classmethod
    def unique_filter(cls, query, *args, **kwargs):
        return query.filter(ZHRandomColumn.slug == kwargs['slug'])


engine = create_engine('postgresql+psycopg2://postgres:123456qq@localhost:5432/lighthouse',
                       encoding='utf-8'.encode())

DBSession = sessionmaker(bind=engine)
