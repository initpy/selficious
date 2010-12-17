#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
#
# This is SELFICIOUS by Yuuta
# UPDATED: 2010-12-17 15:55:46

import logging
import datetime
import urllib
from xml.dom import minidom
import dateutil.parser
import tornado.web
from google.appengine.api import urlfetch
from google.appengine.api import memcache


def parse_xml_bookmarks(data):
    """Parses delcicious xml export and returns a list of bookmarks"""
    bookmarks = []
    dom = minidom.parseString(data)
    for node in dom.getElementsByTagName('post'):
        bookmarks.append({
            'hash':node.getAttribute('hash'),
            'url':node.getAttribute('href'),
            'title':node.getAttribute('description'),
            'description':node.getAttribute('extended'),
            'tags':node.getAttribute('tag').split(' '),
            'time':dateutil.parser.parse(node.getAttribute('time'))
        })
    return bookmarks
    
def keygen(format, *args, **kwargs):
    """generates a key from args and kwargs using format"""
    allargs = args+tuple(kwargs[key] for key in sorted(kwargs.keys()))
    key = format % allargs[0:format.count('%')]
    return key

def memoize(keyformat, time=600, cache_null=False):
    """Decorator to memoize functions using memcache."""
    def decorator(fxn):
        def wrapper(self, *args, **kwargs):
            key = keygen(keyformat, *args, **kwargs)
            data = memcache.get(key)
            if data is not None:
                logging.info('From memcache: %s' % key)
                return data
            data = fxn(self, *args, **kwargs)
            if data or cache_null:
                memcache.set(key, data, time)
            return data
        return wrapper
    return decorator

def unmemoize(keys_list):
    memcache.delete_multi(keys_list)
