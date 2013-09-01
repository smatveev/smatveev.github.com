#!v/bin/python
# -*- mode: python -*-

import os, sys, shutil, gzip
from datetime import datetime
import markdown

TEMPLATE = 'source/templates/index.html'

def source_constructor(filename):
    if not filename.endswith('.md'):
        filename = filename + '.md'
    return os.path.join('source/posts', filename)

def source_deconstructor(filename):
    if filename.endswith('.md'):
        filename = filename[:-3]

    if filename.startswith('source/posts/'):
        filename = filename[len('source/posts/'):]
    return filename

def dest_constructor(filename):
    return os.path.join('blog', source_deconstructor(filename), 'index.html')

def get_source_list():
    sources = []
    for fl in os.listdir('source/posts'):
        if fl.endswith('.md') and fl not in ['archive.md', 'about.md']:
            sources.append(os.path.join('source/posts/', fl))
    return sources

def get_updated_list(sources = get_source_list()):
    rebuild = []
    template_ts = os.path.getmtime(TEMPLATE)
    for fl in sources:
        dest = dest_constructor(fl)
        if not os.path.isfile(dest) or \
            os.path.getmtime(dest) < max(os.path.getmtime(fl), template_ts):
                rebuild.append( fl )
    return rebuild

def load_post(filename):
    date = source_deconstructor(filename)
    sys.stdout.write('>> date = ' + date + '\n')
    subtitle = ""
    if len(date) > len('0000-00-00') and not "archive" in date:
        year, month, day, subtitle = date.split('-', 3)
        date = year + '-' + month + '-' + day
    data = open(filename, 'r').read()
    title, data = data.split('\n', 1)
    if title.startswith('#'):
        junk, title = title.split(' ', 1)
    return {
        'title': title.strip(),
        'file': source_deconstructor(filename),
        'date': date,
        'text': markify(data.strip()),
        'permalink' : subtitle
    }

class MarkExtension(markdown.extensions.Extension):
    MARK_RE = r"(\~\~)(.+?)(\~\~)"
    def extendMarkdown(self, md, md_globals):
        md.inlinePatterns.add('mark', markdown.inlinepatterns.SimpleTagPattern(self.MARK_RE, 'mark'), '<not_strong')

def markify(text):
    return markdown.markdown(text, [MarkExtension(), 'footnotes', 'fenced_code', 'codehilite', 'tables', 'extra', 'nl2br'])

def template(filename):
    body = open(TEMPLATE, 'r').read()
    dv = load_post(filename)
    for key in dv:
        body = body.replace('@' + key + '@', dv[key])
    return body

def write(src):
    dest = dest_constructor(src)
    sys.stdout.write('>> Archive write dest: ' + dest + '\n')
    run = template(src)

    if not os.path.isdir(os.path.dirname(dest)):
        os.makedirs(os.path.dirname(dest))

    with open(dest, 'w') as fl:
        fl.write(run)

def pages():
    write('pages/about.md')

def archive(sources):
    res = ['# Archive', '', '']
    for post in reversed(sources):
        sys.stdout.write('>> Archive current post: ' + post + '\n')
        p = load_post(post)
        res.append('* [{title}](/{file}) ({date})'.format_map(p))
    with open('source/posts/archive.md', 'w') as fl:
        sys.stdout.write('>> Writing archive: \n')
        fl.write('\n'.join(res))
    write('source/posts/archive.md')

def main(args):
    sources = get_source_list() 
    updated = get_updated_list(sources)
    last = sources[-1]
    for sfrom in updated:
        sys.stdout.write('>> ' + sfrom +' -> ' + dest_constructor(sfrom) + ' \n')
        write(sfrom)
    if last in updated:
        sys.stdout.write('>> Index page updated to ' + last + '\n')
        shutil.copy2(dest_constructor(last), 'index.html')
    if (len(updated) > 1 and updated[0] != last) or 'archive' in args:
        archive(sources)
        sys.stdout.write('>> Archive updated\n')
    if 'pages' in args:
        pages()
        sys.stdout.write('>> Pages updated\n')

if __name__ == '__main__':
    main(sys.argv[1:])