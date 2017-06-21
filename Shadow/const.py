# coding: utf-8
class ChoiceBase(object):
    __choices__ = ()

    def get_choices(self):
        return self.__choices__

    @classmethod
    def get_display_name(cls, value):
        _names = dict(cls.__choices__)
        return _names.get(value) or ""

    @classmethod
    def all_elements(cls):
        _dict = dict(cls.__choices__)
        return _dict.keys()


class ProtocolChoice(ChoiceBase):
    HTTP = 1
    HTTPS = 2

    __choices__ = (
        (HTTP, u'HTTP'),
        (HTTPS, u'HTTPS'),
    )