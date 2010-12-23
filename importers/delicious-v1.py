#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
#
# This is SELFICIOUS by Yuuta
# UPDATED: 2010-12-23 18:54:07

import urllib2
import base64
import hashlib
from xml.dom import minidom
import dateutil.parser
from importers import BaseImporter

class DeliciousV1Importer(BaseImporter):
    """
    A Delicious posts importer for old accounts i.e. Not tied with Yahoo
    accounts - Using the user's username and password.
    """
    service_name = 'delicious-v1'
    service_verbose_name = "Old Delicious Account"
    form = """
        <p>
            <label for="username">Delicious Username</label>
            <input name="username" class="text" type="text" id="username"/>
        </p>
        <p>
            <label for="password">Delicious Password</label>
            <input name="password" class="text" type="password" id="password"/>
        </p>
        """

    def __init__(self, tornado_handler):
        self.url = "https://api.del.icio.us/v1/posts/all"
        self.domain = "https://api.del.icio.us/"
        self.user = tornado_handler.get_argument("username", "")
        self.password = tornado_handler.get_argument("password", "")
        super(DeliciousV1Importer, self).__init__(tornado_handler)

    def fetch_posts(self):
        try:
            passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passman.add_password(None, self.domain, self.user, self.password)
            authhandler = urllib2.HTTPBasicAuthHandler(passman)
            opener = urllib2.build_opener(authhandler)
            urllib2.install_opener(opener)
            self.data = urllib2.urlopen(self.url).read()
            self.success = True
        except:
            self.success = False
            self.error = "fetch"
            self.data = None

    def posts(self):
        self.fetch_posts()
        if self.success:
            posts = []
            dom = minidom.parseString(self.data)
            h = hashlib.sha1()
            for node in dom.getElementsByTagName('post'):
                h.update(node.getAttribute('href'))
                posts.append({
                    'hash':h.hexdigest(),
                    'url':node.getAttribute('href'),
                    'title':node.getAttribute('description'),
                    'description':node.getAttribute('extended'),
                    'tags':node.getAttribute('tag').split(' '),
                    'time':dateutil.parser.parse(node.getAttribute('time'))
                })
            return posts
        else:
            return []
