#!/usr/bin/env python
# -*- coding: utf-8 -*- 
#
# This is SELFICIOUS by Yuuta
# UPDATED: 2010-12-23 19:08:39

import logging
import hashlib
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

from utils import memoize, unmemoize
import importers
import settings


class Entry(db.Model):
    """
    A single entry.
    service: the service's name from which the entry comes -may be empty
    hash: a hash (sha1) of the url
    """
    service = db.StringProperty(required=False)
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
        error = self.get_argument('error', "")
        self.render("home.html", entries=entries, import_success=import_success,
                error_message=importers.messages[error])


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
            h = hashlib.sha1()
            h.update(self.get_argument("url", ""))
            entry = Entry(
                service="internal",
                title=self.get_argument("title", ""),
                description=self.get_argument("description", ""),
                url=self.get_argument("url", ""),
                hash=h.hexdigest(),
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
        services = importers.list()
        self.render("import.html", services=services)

    @administrator
    def post(self):
        service = self.get_argument("service", "")
        try:
            service_class = importers.new(service)
            importer = service_class(self)
            posts = importer.posts()
            if importer.success:
                self._save_posts(posts, service)
                self.redirect("/?imported=1")
            else:
                self.redirect("/?imported=0&error=%s"%importer.error)
        except NotImplementedError:
            self.redirect("/?imported=0&error=unknown_service")

    def _save_posts(self, posts, service):
        for post in posts:
            entry = Entry(
                service=service,
                hash=post['hash'],
                url=post['url'],
                title=post['title'],
                description=post['description'],
                time=post['time'],
                tags = [db.Category(tag) for tag in post['tags'] if tag ]
            )
            entry.put()
        self.free_cache()
        

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
    (r"/post", BookmarkHandler),
    (r"/import", ImportHandler),
    (r"/index", tornado.web.RedirectHandler, {"url": "/archive"}),
    (r"/delete", DeleteHandler),
], **settings)


def main():
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == "__main__":
    main()
