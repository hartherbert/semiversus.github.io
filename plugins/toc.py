'''
toc
===================================

This plugin generates tocs for pages and articles.
'''

from __future__ import unicode_literals

import logging
import re

from bs4 import BeautifulSoup, Comment

from pelican import contents, signals
from pelican.utils import python_2_unicode_compatible, slugify


logger = logging.getLogger(__name__)

'''
https://github.com/waylan/Python-Markdown/blob/master/markdown/extensions/headerid.py
'''
IDCOUNT_RE = re.compile(r'^(.*)_([0-9]+)$')


def unique(id, ids):
    """ Ensure id is unique in set of ids. Append '_1', '_2'... if not """
    while id in ids or not id:
        m = IDCOUNT_RE.match(id)
        if m:
            id = '%s_%d' % (m.group(1), int(m.group(2)) + 1)
        else:
            id = '%s_%d' % (id, 1)
    ids.add(id)
    return id
'''
end
'''


@python_2_unicode_compatible
class HtmlTreeNode(object):
    def __init__(self, parent, header, level, id):
        self.children = []
        self.parent = parent
        self.header = header
        self.level = level
        self.id = id

    def add(self, new_header, ids):
        new_level = new_header.name
        new_string = new_header.string
        new_id = new_header.attrs.get('id')

        if not new_string:
            new_string = new_header.find_all(
                    text=lambda t: not isinstance(t, Comment),
                    recursive=True)
            new_string = "".join(new_string)

        if not new_id:
            new_id = slugify(new_string, ())

        new_id = unique(new_id, ids)  # make sure id is unique
        new_header.attrs['id'] = new_id
        if(self.level < new_level):
            new_node = HtmlTreeNode(self, new_string, new_level, new_id)
            self.children += [new_node]
            return new_node, new_header
        elif(self.level == new_level):
            new_node = HtmlTreeNode(self.parent, new_string, new_level, new_id)
            self.parent.children += [new_node]
            return new_node, new_header
        elif(self.level > new_level):
            return self.parent.add(new_header, ids)

    def __str__(self):
        if self.parent:
          ret = "<a href='#{0}'>{1}</a>".format(
                  self.id, self.header)
        else:
          ret = ""

        if self.children:
            ret += "<ul class=\"nav\">{}</ul>".format('{}'*len(self.children)).format(
                    *self.children)


        if not self.parent:
            ret = "{}".format(ret)
        else:
            ret = "<li>{}</li>".format(ret)

        return ret


def init_default_config(pelican):
    from pelican.settings import DEFAULT_CONFIG

    TOC_DEFAULT = {
        'TOC_HEADERS': '^h[1-6]',
        'TOC_RUN': 'true'
    }

    DEFAULT_CONFIG.setdefault('TOC', TOC_DEFAULT)
    if(pelican):
        pelican.settings.setdefault('TOC', TOC_DEFAULT)


def generate_toc(content):
    if isinstance(content, contents.Static):
        return
    if str(content.metadata.get('toc', '')).lower()=='false':
      content.toc=None
      return

    _toc_run = content.metadata.get(
            'toc_run',
            content.settings['TOC']['TOC_RUN'])
    if not _toc_run == 'true':
        return

    all_ids = set()
    title = content.metadata.get('title', 'Title')
    tree = node = HtmlTreeNode(None, title, 'h0', '')
    soup = BeautifulSoup(content._content, 'html.parser')
    settoc = False

    try:
        header_re = re.compile(content.metadata.get(
            'toc_headers', content.settings['TOC']['TOC_HEADERS']))
    except re.error as e:
        logger.error("TOC_HEADERS '%s' is not a valid re\n%s",
                     content.settings['TOC']['TOC_HEADERS'])
        raise e

    for header in soup.findAll(header_re):
        settoc = True
        node, new_header = node.add(header, all_ids)
        header.replaceWith(new_header)  # to get our ids back into soup

    if (settoc):
        tree_string = '{}'.format(tree)
        tree_soup = BeautifulSoup(tree_string, 'html.parser')
        content.toc = tree_soup.decode(formatter='html')
    content._content = soup.decode(formatter='html')


def register():
    signals.initialized.connect(init_default_config)
    signals.content_object_init.connect(generate_toc)

