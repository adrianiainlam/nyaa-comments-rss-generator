#!/usr/bin/env python3

# Nyaa Comments RSS Generator
# Copyright (c) 2019 Adrian I Lam <spam@adrianiainlam.tk> s/spam/me/
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from http.server import BaseHTTPRequestHandler, HTTPServer
import datetime
from feedgen.feed import FeedGenerator
import AdvancedHTMLParser
import requests


class NyaaComments(BaseHTTPRequestHandler):
  def do_GET(self):
    if self.path == '/':
      # return home page
      self.send_response(200)
      self.send_header('Content-type', 'text/plain')
      self.end_headers()
      self.wfile.write(bytes('''
Welcome to Nyaa Comments RSS Generator.

DISCLAIMER: This site is not affiliated with Nyaa.si

To use:
 For Nyaa:
  - Get your torrent number
    For example, https://nyaa.si/view/1002779 -> number is 1002779
  - Your feed URL is https://nyaacomments.tk/1002779
 For Sukebei.nyaa:
  Prepend 's' before the number
    For example, https://nyaacomments.tk/s1002779

Bug reports welcome at <spam@adrianiainlam.tk> (replace "spam" with "me"),
or on <https://github.com/adrianiainlam/nyaa-comments-rss-generator>.

IMPORTANT: Please avoid updating your feeds too often. If you really
need to parse the feeds often, consider running this script locally
(see GitHub link above).

UPDATE: (2019-04-11) Recently, Nyaa has been serving HTTP 429 (Too Many
Requests). I've thus removed threading support, so that my server only
sends them one request at a time. Depending on network latency, this
may cause your RSS client to report request timeouts, but I can't think
of easy ways to fix this. Running this script locally (see GitHub link
above) may help.
''', 'utf-8'))

    else:
      sukebei = False
      try:
        if self.path[1] == 's':
          sukebei = True
          nyaaid = int(self.path[2:])
        else:
          nyaaid = int(self.path[1:])
      except ValueError:
        self.send_response(404)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(bytes('Error: Not a valid torrent number', 'utf-8'))
        return

      if sukebei:
        url = "https://sukebei.nyaa.si/view/" + str(nyaaid)
      else:
        url = "https://nyaa.si/view/" + str(nyaaid)
      useragent = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0"
      req = requests.get(url, headers={"user-agent": useragent})

      self.send_response(req.status_code)

      if req.status_code != 200:
        # return error page with upstream error code
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(bytes('Nyaa returns HTTP status ' + str(req.status_code), 'utf-8'))

      else:
        parser = AdvancedHTMLParser.AdvancedHTMLParser()
        parser.parseStr(req.text)

        fg = FeedGenerator()
        fg.link(href=url, rel='alternate')
        htmltitle = parser.getElementsByTagName('title')[0].innerHTML
        fg.title('Comments for ' + htmltitle)
        fg.id(url)
        fg.link(href='https://nyaacomments.tk' + self.path, rel='self')

        i = 1
        timestamp = None
        while True:
          cmt = parser.getElementById('com-' + str(i))
          if cmt is None:
            break
          authortag = cmt.filter(tagname='a', href__contains='/user/')[0]
          author = authortag.href.replace('/user/', '')
          link = url + "#com-" + str(i)

          tsanchor = cmt.getElementsByAttr('href', '#com-' + str(i))[0]
          timestamp = int(tsanchor.getChildren()[0].getAttribute('data-timestamp'))
          content = cmt.getElementsByClassName('comment-content')[0].innerHTML

          fe = fg.add_entry()
          fe.id(link)
          fe.title('Comment by ' + author + ' on ' + htmltitle)
          fe.author({'name': author})
          fe.pubDate(datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc))
          fe.updated(datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc))
          fe.link(href=link, rel='alternate')
          fe.content(content, type='html')

          i = i + 1


        #set feed last update time to publish time of last comment
        if timestamp is not None:
          fg.updated(datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc))

        self.send_header('Content-type', 'application/atom+xml')
        self.end_headers()

        self.wfile.write(bytes(fg.atom_str(pretty=True).decode('utf-8').replace('&amp;','&').replace('&#10;','&lt;br&gt;'), 'utf-8'))

        return


if __name__ == '__main__':
    server = HTTPServer(('localhost', 2800), NyaaComments)
    server.serve_forever()
