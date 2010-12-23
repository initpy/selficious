#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
#
# This is SELFICIOUS by Yuuta
# UPDATED: 2010-12-23 18:58:32

import urllib2
import base64
import hashlib
from xml.dom import minidom
import dateutil.parser
from importers import BaseImporter

class DeliciousLocalXMLImporter(BaseImporter):
    """
    Imports bookmarks from an XML file saved from delicious. To get this kind of
    files, visit <a
    href="https://api.del.icio.us/v1/posts/all">http://api.del.icio.us/v1/posts/all
    </a> (if you're an old delicious user) or <a
    href="https://api.del.icio.us/v2/posts/all">http://api.del.icio.us/v2/posts/all
    </a> (if you're using delicious with your yahoo credentials &mdah;Be sure to
    be logged in (yahoo) first) 
    """
    service_name = 'delicious-xml'
    service_verbose_name = "Local XML file saved from delicious"
    form = """
        <p>
        <label for="xmlfile" class="gauche">Upload your XML file: </label>
        <input id="xmlfile" type="file" name="xmlfile" />
        </p> 
        """

    def __init__(self, tornado_handler):
        try:
            uploaded_file = tornado_handler.request.files['xmlfile'][0]
            self.data = uploaded_file['body']
            self.success = True
        except:
            self.success = False
            self.error = 'fetch'
        super(DeliciousLocalXMLImporter, self).__init__(tornado_handler)

    def posts(self):
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
