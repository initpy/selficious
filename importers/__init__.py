#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
#
# This is SELFICIOUS by Yuuta
# UPDATED: 2010-12-23 20:35:08

import os
import sys

messages = {
        "":"",
        "fetch": "Unable to fetch your posts",
        "parse": "Unable to parse your posts",
        "unknown_service": "Don't know how to import from this service",
}

IMPORTERS = {}

class ImporterMeta(type):
    def __init__(cls, name, bases, dict):
        if not hasattr(cls, 'service_name'):
            cls.service_name = name
        if not hasattr(cls, 'verbose_service_name'):
            cls.verbose_service_name = name
        if not hasattr(cls, 'form'):
            cls.form = ''
        super(ImporterMeta, cls).__init__(name, bases, dict)
        if name != 'BaseImporter':
            IMPORTERS.update({cls.service_name:cls})


class BaseImporter(object):
    """
    A base class for posts importers
    All derived classes MUST include a self.success property which tells if the
    import was successfull AND a method self.posts() which will return a list of
    dicts representing the fetched posts.
    Thses classes are __init__'iated using a tornado handler which will give
    them their attributes values using its (the handler's) method get_argument()
    """
    __metaclass__ = ImporterMeta

    def __init__(self, tornado_handler):
        pass

    def fetch_posts(self):
        """Overrided in children classes to fetch the posts"""
        raise NotImplementedError

    def posts(self):
        """Overrided in children classes to return a list of posts"""
        raise NotImplementedError


def find_importers():
    '''find all files in the importer directory and imports them'''
    importer_dir = os.path.dirname(os.path.realpath(__file__))
    importer_files = [x[:-3] for x in os.listdir(importer_dir) if 
            x.endswith(".py")]
    sys.path.insert(0, importer_dir)
    for importer in importer_files:
        mod = __import__(importer)

def new(service_name):
    find_importers()
    try:
        return IMPORTERS[service_name]
    except KeyError:
        raise NotImplementedError

def list():
    find_importers()
    return [
            dict(
                name=i.service_name,
                verbose_name=i.service_verbose_name,
                form = i.form,
                description = i.__doc__,
                ) for i
            in IMPORTERS.values()
    ]
