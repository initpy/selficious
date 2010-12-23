#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
#
# This is SELFICIOUS by Yuuta
# UPDATED: 2010-12-22 22:28:40

import logging
from google.appengine.api import memcache

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
