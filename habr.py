# coding: UTF-8
# Read *.txt *.md files from directory name, passed as parameter, download images by links found in texts
# and make replacements in text
from datetime import datetime
import os
import re
import markdown
import requests
import sys


def download_images(text, out_dir):
    i = 0
    links = list(re.finditer(re.compile(
        "(?:<img[^>]*src=[\'\"]([^\'\"]+?habrastorage[^\'\"]+))", re.IGNORECASE), text)) + list(re.finditer(re.compile(
        "(?:!\[image\]\(([^\)]+?habrastorage[^\)]+)\))", re.IGNORECASE), text))
    for m in links:
        link = m.group(1)
        m.groups()
        print link
        link = link.replace("habrastorage.org", "hsto.org")
        if link[:2] == "//":
            link = "http:%s" % link
        if link[:4] != "http":
            link = "http://%s" % link
        resp = requests.get(link, allow_redirects=True)
        if not resp or len(resp.content) == 0:
            print("repeat request %s" % link)
            resp = requests.get(link)
        if resp:
            i += 1
            file_name = os.path.join(out_dir, "%d_%s" % (i, link[link.rfind("/")+1:]))
            f = open(file_name, "wb")
            f.write(resp.content)
            f.close()


def get_headers_map(text):
    headers_map = {}
    headers = list(set(re.findall(r'<h(\d)>', text)))
    if headers:
        h_level = 1
        for h_i in sorted(headers):
            h_level += 1
            headers_map["<h%s>" % h_i] = "<h%d>" % h_level
            headers_map["</h%s>" % h_i] = "</h%d>" % h_level
    print(headers_map)
    return headers_map


class ImageNumbers(object):
    def __init__(self, dt, start=1):
        self.dt = dt
        self.count = start - 1

    def __call__(self, match):
        self.count += 1
        return '<a href="/wp-content/uploads/%(year)s/%(month)02d/%(count)s_%(name)s"><img src="/wp-content/uploads/' \
               '%(year)s/%(month)02d/%(count)s_%(name)s" alt="image" class="aligncenter size-full wp-image-1000" />' \
               '</a>' % {'year': self.dt.year, 'month': self.dt.month, 'count': self.count,
                         'name': match.group(1).lower()}


def ignore_tags(text):
    for tag in ("<blockquote>", "</blockquote>", "<oembed>", "</oembed>", "</spoiler>", "<spoiler>"):
        text = text.replace(tag, "")
    return text


def make_html_replaces(text):
    for h_src, h_real in get_headers_map(text).items():
        text = text.replace(h_src, h_real)
    text = cut_tag(text)
    text = text.replace("<source>", "[code]")
    text = text.replace("</source>", "[/code]")
    text = text.replace("</source >", "[/code]")
    text = ignore_tags(text)
    text = text.replace(u"…".encode("utf-8"), "&hellip;")
    text = re.sub(
        r'<a[^>]+?href=[\'\"]https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([^&?=/]+)[^>]+>([^<]+?)</a>',
        'http://youtu.be/\g<1>\n\g<2>', text)
    text = re.sub(r'<video[^>].*?>(https?://youtu[^<]+?)</video>', '\g<1>\n', text)
    text = re.sub(r'<source lang=[\'\"]?([^\"\']+)[\'\"]?>', '[code lang="\g<1>"]', text)
    text = re.sub(r'<spoiler title=[\'\"]([^\"\']+)[\'\"]>', '<p>\g<1></p>', text)
    text = img_replace(text)
    return text


def make_md_replaces(text):
    md = markdown.Markdown()
    text = md.convert(text.decode('utf-8')).encode('utf-8')
    text = cut_tag(text)
    text = ignore_tags(text)
    text = img_replace(text)
    return text


def cut_tag(text):
    text = text.replace("<habracut/>", "<!--more-->")
    text = text.replace("<habracut />", "<!--more-->")
    text = text.replace("<habracut>", "<!--more-->")
    text = text.replace("<cut>", "<!--more-->")
    text = text.replace("<cut/>", "<!--more-->")
    text = text.replace("<cut />", "<!--more-->")
    return re.sub(r'<cut[^>]+?text=[\'\"]([^\'\"]+)[\'\"][^>]+>', '<!--more \g<1>-->', text)


def img_replace(text):
    dt = datetime.now()
    text = re.sub(r'<img[^>]*src=[\'\"](?:https?)?[^\'\">]+?habrastorage\.org/[^\"\']+?/([^/\.]+\.(?:png|gif|PNG|GIF|jpe?g|JPE?G))[^>]+>',
                  ImageNumbers(dt), text)
    return text


def process_article(file_name):
    right_dot_pos = file_name.rfind(".")
    file_ext = file_name[right_dot_pos:]
    print(file_ext)
    out_dir = file_name[:right_dot_pos]
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    f = open(file_name, 'r')
    article = f.read()
    f.close()
    download_images(article, out_dir)
    text = None
    if file_ext == ".txt":
        text = make_html_replaces(article)
    elif file_ext == ".md":
        text = make_md_replaces(article)
    if text:
        file_name = os.path.join(out_dir, "out.html")
        f = open(file_name, "w")
        f.write(text)
        f.close()


def process_dir(dir_name):
    for f in os.listdir(dir_name):
        if re.search(r'.+\.(?:md|txt)$', f):
            process_article(os.path.join(dir_name, f))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: %s <directory>" % sys.argv[0]
        sys.exit(2)
    else:
        process_dir(sys.argv[1])
