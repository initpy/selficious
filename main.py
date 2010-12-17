#!/usr/bin/env python
# -*- coding: utf-8 -*- 
#
# This is SELFICIOUS by Yuuta
# UPDATED: 2010-12-17 15:55:54

import logging
import base64
import urllib2
import uuid
import functools
import os
import os.path
import re
import tornado.web
import tornado.wsgi
import unicodedata
import wsgiref.handlers

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api import urlfetch

from utils import parse_xml_bookmarks, memoize, unmemoize
import settings

DELICIOUS_XML_EXPORT = "https://api.del.icio.us/v1/posts/all"


class Entry(db.Model):
    """A single bookmark entry."""
    hash = db.StringProperty(required=True)
    title = db.StringProperty(required=True)
    description = db.TextProperty()
    url = db.LinkProperty(required=True)
    time = db.DateTimeProperty(auto_now_add=True)
    tags = db.ListProperty(db.Category)


def administrator(method):
    """Decorate with this method to restrict to site admins."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            if self.request.method == "GET":
                self.redirect(self.get_login_url())
                return
            raise web.HTTPError(403)
        elif not self.current_user.administrator:
            if self.request.method == "GET":
                self.redirect("/")
                return
            raise web.HTTPError(403)
        else:
            return method(self, *args, **kwargs)
    return wrapper


class BaseHandler(tornado.web.RequestHandler):
    """Implements Google Accounts authentication methods."""
    def get_current_user(self):
        user = users.get_current_user()
        if user: user.administrator = users.is_current_user_admin()
        return user

    def get_login_url(self):
        return users.create_login_url(self.request.uri)

    def render_string(self, template_name, **kwargs):
        return tornado.web.RequestHandler.render_string(
            self, template_name, users=users, **kwargs)

    def slugify(self, title):
        slug = unicodedata.normalize("NFKD", title).encode("ascii", "ignore")
        slug = re.sub(r"[^\w]+", " ", slug)
        return "-".join(slug.lower().strip().split())

    @memoize('/entries/recent')
    def get_recent_entries(self):
        entries = db.Query(Entry).order("-time").fetch(limit=5)
        return entries

    @memoize('/entries/home')
    def get_home_entries(self):
        entries = db.Query(Entry).order("-time").fetch(limit=10)
        return entries

    @memoize('/entries/archive')
    def get_archive_entries(self):
        entries = db.Query(Entry).order("-time")
        return entries

    @memoize('/entries/tag/%s')
    def get_tagged_entries(self, tag):
        entries = db.Query(Entry).filter("tags =", tag).order("-time")
        return entries

    def free_cache(self, tags=[]):
        """Use utils.unmemoize to delete stuff from memcache"""
        unmemoize([ "/entries/recent", "/entries/home", "/entries/archive"])
        unmemoize(["/entries/tag/%s" % tag for tag in tags])


class HomeHandler(BaseHandler):
    def get(self):
        entries = self.get_home_entries()
        import_success = self.get_argument('imported', None)
        if not entries:
            if not self.current_user or self.current_user.administrator:
                self.redirect("/bookmark")
                return
        self.render("home.html", entries=entries, import_success=import_success)


class ArchiveHandler(BaseHandler):
    def get(self):
        entries = self.get_archive_entries()
        self.render("archive.html", entries=entries)


class TagHandler(BaseHandler):
    def get(self, tag):
        entries = self.get_tagged_entries(tag)
        self.render("tag.html", tag=tag, entries=entries)


class BookmarkHandler(BaseHandler):
    @administrator
    def get(self):
        key = self.get_argument("key", None)
        entry = Entry.get(key) if key else None
        self.render("form.html", entry=entry)

    @administrator
    def post(self):
        key = self.get_argument("key", None)
        if key:
            entry = Entry.get(key)
            entry.title = self.get_argument("title", "")
            entry.description = self.get_argument("description", "")
            entry.url = self.get_argument("url", "")
        else:
            entry = Entry(
                title=self.get_argument("title", ""),
                description=self.get_argument("description", ""),
                url=self.get_argument("url", ""),
                hash=uuid.uuid4().hex,
            )
        tags = set([self.slugify(unicode(tag)) for tag in
            self.get_argument("tags", "").split(",")])
        tags = [db.Category(tag) for tag in tags if tag]
        entry.tags = tags
        entry.put()
        self.free_cache(tags=entry.tags)
        self.redirect("/")


class ImportHandler(BaseHandler):
    @administrator
    def get(self):
        self.render("import.html")

    @administrator
    def post(self):
        duser = self.get_argument("duser")
        dpswd = self.get_argument("dpswd")
        try:
            base64string = base64.encodestring('%s:%s' % (duser, dpswd))[:-1]
            headers = {
                    "Authorization": "Basic %s" % base64string,
                }
            result = urlfetch.fetch(DELICIOUS_XML_EXPORT, headers=headers)
            self._save_bookmarks(result.content)
        except:
            self.redirect("/?imported=99")

    def _save_bookmarks(self, data):
        bookmarks = parse_xml_bookmarks(data)
        for bookmark in bookmarks:
            entry = Entry(
                hash=bookmark['hash'],
                url=bookmark['url'],
                title=bookmark['title'],
                description=bookmark['description'],
                time=bookmark['time'],
                tags = [db.Category(tag) for tag in bookmark['tags'] if tag ]
            )
            entry.put()
        self.free_cache()
        self.redirect("/?imported=1")
        


class DeleteHandler(BaseHandler):
    @administrator
    def get(self):
        key = self.get_argument("key")
        try:
            entry = Entry.get(key)
            self.free_cache(tags=entry.tags)
        except db.BadKeyError:
            raise tornado.web.HTTPError(404)
        entry.delete()
        self.redirect("/")


class EntryModule(tornado.web.UIModule):
    def render(self, entry):
        return self.render_string("modules/entry.html", entry=entry)


settings = {
    "site_title": getattr(settings, 'SITE_TITLE', u'My Bookmarks'),
    "template_path": os.path.join(os.path.dirname(__file__), "templates"),
    "ui_modules": {"Entry": EntryModule,},
    "xsrf_cookies": True,
    "debug": os.environ.get("SERVER_SOFTWARE", "").startswith("Development/"),
}

application = tornado.wsgi.WSGIApplication([
    (r"/", HomeHandler),
    (r"/archive", ArchiveHandler),
    (r"/tag/([^/]+)/?", TagHandler),
    (r"/bookmark", BookmarkHandler),
    (r"/import", ImportHandler),
    (r"/index", tornado.web.RedirectHandler, {"url": "/archive"}),
    (r"/delete", DeleteHandler),
], **settings)


def main():
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == "__main__":
    main()
