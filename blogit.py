#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import sys
import os
import json
from datetime import datetime, timedelta
import re, shutil, gzip, functools

sys.path.insert(0, 'libs/')
import markdown2 as markdown
import pystache

import codecs

current_date = datetime.now().strftime('%Y-%m-%d')

def loadConfigs(path=os.getcwd()):
    fname = os.path.join(path, 'config.json')
    if not os.path.isfile(fname):
        return None
    return json.load(open(fname))


def saveto(fres, addflag = ''):
    dname = os.path.dirname(fres)
    try:
        os.makedirs(dname)
    except:
        pass
    return open(fres, 'w' + addflag)


config = loadConfigs()


def tags_cludge(tag):
    c = tag.group(1)
    if c == '*':
        tag = '<b style="font-size: 1.6em; color: gold;">?</b>'
    else:
        tag = "<small>#" + c + "</small>"
    return ' ' + tag


def makeHtml(inbound):
    res = []
    for line in inbound.split('\n'):
        line = line.strip()
        if line.startswith('>>') and line.endswith('<<'):
            line = line[2:-2].strip()
            if line.startswith('!['):
                # inline image!
                tp, url = line[2:-1].split('](')
                if tp == 'center':
                    line = '<div style="text-align: center"><img src="' + \
                    url + \
                    '" style="float: none" /></div>'
            else:
                raise Error('Unknown inline')
        res.append(line)
    res = '\n'.join(res)

    res = markdown.markdown(res, extras=["cuddled-lists", "footnotes"])

    res = re.sub(' \#([a-zA-Z0-9\*]+)', tags_cludge, res)
    res = re.sub('\{([a-zA-Z0-9\*]+)\}', tags_cludge, res)
    return res


def get_true_page_name(page = current_date):
    if 'yesterday' in page:
        page = page.replace('yesterday', (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'))
    elif 'tomorrow' in page:
        page = page.replace('tomorrow', (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'))
    elif 'today' in page:
        page = page.replace('today', datetime.now().strftime('%Y-%m-%d'))
    if '.' in page:
        page = page.rsplit('.', 1)[0]
    return page


def get_true_entry(page, force, index):
    fpath = os.path.join(config['local']['posts'], page + '.md')

    with index as idx:
        if not force:
            if page in idx and os.path.getmtime(fpath) <= idx[page]['cdate']:
                return None

    entry = MarkDownEntry(page)

    if page not in idx['idx']:
        entry.is_index = True
    else:
        last = None
        for x in perversed(idx['idx']):
            if 'draft' not in idx[x] or idx[x]['draft'] == False:
                last = x
                break
        if last == page:
            entry.is_index = True

    return entry


def gen_page(page, force, index):
    page = get_true_page_name(page)
    entry = get_true_entry(page, force, index)
    if not entry:
        return

    entry.do(config['local']['templates']['post'])
    sys.stdout.write('File %s written\n' % entry.result)
    if entry.is_index:
        entry.do_to(config['local']['templates']['post'],
                    config['local']['results']['path'] + 'index.html')
        sys.stdout.write('Page ' + page + ' also is index\n')

    return entry


def put_to_index(index, entry):
    page = entry.page
    index[page] = dict(
        permalink=entry.permalink,
        title=entry.title,
        cdate=entry.cdate,
        fdate=entry.fdate,
    )

    if page not in index['idx']:
        index['idx'].append(page)


def _perversed_sort(x,y):
    x = extract_numbers(x)
    y = extract_numbers(y)
    return -1 if x > y else 1 if x < y else 0        


def perversed(vd):
    "Sort dictionary in my own way, aha"
    return sorted(vd, key=functools.cmp_to_key(_perversed_sort))        


class Index(dict):
    def __init__(self, filename=None, ro=False, *args, **kwds):
        self.filename = filename if filename else config['local']['index']
        self.ro = ro
        # if os.path.isfile(self.filename):
        #     self.load(self.filename)
        dict.__init__(self, *args, **kwds)
        if 'idx' not in self:
            self['idx'] = []

    def load(self, fd):
        try:
            return self.update(json.load(open(fd, 'r')))
        except Exception:
            pass

    def sync(self):
        'Write dict to disk'
        if self.ro:
            return
        with saveto(self.filename) as fl:
            json.dump(self, fl, ensure_ascii=False, indent=True)

    def close(self):
        self.sync()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


class Entry:
    def __init__(self, page, empty=False):
        self.is_index = False
        if '/' in page:
            self.fullpath = page
            self.page = os.path.basename(page).split('.')[0]
        else:
            self.page = page
            post_path = config['local']['posts']
            self.fullpath = os.path.join(post_path, page)
        if '.' not in self.fullpath:
            self.fullpath = self.fullpath + '.md'
        self.title = None
        self.cdate = os.path.getmtime(self.fullpath)
        self.fdate = self.cdate
        if not empty and os.path.isfile(self.fullpath):
            self.load()

    # def parse(self):
    #     pass

    def load(self):
        self.content = open(self.fullpath).read()
        self.parse()


class MarkDownEntry(Entry):
    def parse(self):
        if self.content.startswith('---'):
            headers, rest = self.content[3:].split('---', 1)
            self.headers = {}
            for key, value in (line.strip().split(': ', 1)
                                for line in headers.split('\n')
                                        if not line.startswith('#') and ':' in line):
                self.headers[key.lower()] = value
            self.content = rest
            if 'title' in self.headers:
                self.title = self.headers['title']
            if 'date' in self.headers:
                self.fdate = self.headers['date']
        elif self.content.startswith('# '):
            title, rest = self.content.split('\n', 1)
            hashmash, self.title = title.split(' ', 1)
            self.content = rest
        else:
            title, rest = self.content.split('\n', 1)
            self.title = title
            self.content = rest
        self.content = makeHtml(self.content)
        self.result = os.path.join(config['local']['results']['posts'],
                                                 self.page[11:], 'index.html')
        self.permalink = config['site'] + config['local']['results']['site'] + self.page[11:]


    def do(self, template):
        return self.do_to(template, self.result)

    def do_to(self, template, fpath):
        print(template)
        res = pystache.render(open(template, 'r').read(),
            {
                'conf': config, 'title': self.title,
                'cdate': self.cdate, 'fdate': self.fdate,
                'content': self.content.replace('\n', ' '),
                'page': self.page,
                'permalink': self.permalink
            })
        with saveto(fpath) as fl:
            fl.write(res)


class Archive:
    def __init__(self, idx):
        self.idx = idx
        self.results = os.path.join(config['local']['results']['archive'], 'index.html')

    def do(self, template):
        items = []
        for x in perversed(self.idx['idx']):
            items.append({
                'fname': self.idx[x]['permalink'],
                'subtitle': self.idx[x]['title'],
                })
        res = pystache.render(open(template, 'r').read(),
            {
                'conf': config,
                'title': 'Archive',
                'items': items,
                'permalink': config['site'] + '/archive'
            })
        with saveto(self.results) as fl:
            fl.write(res)


def regenCSS():
    '''regen .less files to style.css'''
    shutil.copy("style.css", "post/style.css")
    cwd = os.getcwd()
    # os.chdir(config['local']['templates']['path'] + 'bootstrap/less')
    # os.system("lessc -x style.less | gzip -c -9 > " + \
    #             cwd + '/' + config['local']['results']['path'] + 'style.css')
    # os.chdir(cwd)  


def archive():
    '''regen /arhive page'''
    f = Archive(Index(ro=True))
    f.do(config['local']['templates']['archive'])
    sys.stdout.write('Archive ' + f.results + ' saved\n')


def regen(wipe=False, force=False, noindex=False, andsync=False, sections=False):
    """regenerate index and all pages"""
    cache = Index(ro=True)
    with Index() as idx:
        if wipe:
            idx['idx'] = []
            cache['idx'] = []
        for item in os.listdir(config['local']['posts']):
            entry = gen_page(page=item, force=force, index=cache)
            if entry:
                put_to_index(index=idx, entry=entry)
    # if sections:
    #     for item in os.listdir(config['local']['section']):
    #         entry = gen_section(page=item)
    if not noindex:
         regenCSS()
         archive()
    #     feed()
    # if andsync:
    #     sync()


regen()
# regenCSS()