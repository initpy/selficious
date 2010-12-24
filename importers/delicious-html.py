#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
#
# This is SELFICIOUS by Yuuta
# UPDATED: 2010-12-24 15:06:39

import hashlib
import BeautifulSoup
import datetime
from importers import BaseImporter

class DeliciousLocalHTMLImporter(BaseImporter):
    """
    Imports bookmarks from an HTML file saved from delicious. To get this kind of
    files, visit <a
    href="https://secure.delicious.com/settings/bookmarks/export">
    https://secure.delicious.com/settings/bookmarks/export
    </a> &mdash;make sure to check "include my tags" and "include my notes"
    """
    service_name = 'delicious-html'
    service_verbose_name = "Local HTML bookmarks file saved from delicious"
    form = """
        <p>
        <label for="htmlfile" class="gauche">Upload your HTML file: </label>
        <input id="htmlfile" type="file" name="htmlfile" />
        </p> 
        """
    def __init__(self, tornado_handler):
        try:
            uploaded_file = tornado_handler.request.files['htmlfile'][0]
            self.data = uploaded_file['body']
            self.success = True
        except:
            self.success = False
            self.error = 'fetch'
        super(DeliciousLocalHTMLImporter, self).__init__(tornado_handler)

    def posts(self):
        if self.success:
            posts = []
            soup = BeautifulSoup.BeautifulSoup(self.data)
            anchors = soup.findAll("a")
            h = hashlib.sha1()
            for a in anchors:
                h.update(a['href'])
                if a.parent.nextSibling and a.parent.nextSibling.name  == 'dd':
                    text = unicode(a.parent.nextSibling.string)
                else:
                    text = ''
                posts.append({
                    'hash':h.hexdigest(),
                    'url':a['href'],
                    'title':unicode(a.string),
                    'description':text,
                    'tags':unicode(a['tags']).split(','),
                    'time':datetime.datetime.fromtimestamp(float(a['add_date']))
                })
            return posts
        else:
            return []
