#!/usr/bin/env python

""" A script to crawl the Gaia GPS user manual and convert its contents
to a PDF document.
  
   Created by Anting Shen on 8/19/13.
   Copyright (c) 2013 TrailBehind, Inc. All rights reserved.

"""

import HTMLParser
import logging
import sys
import urllib2
import urlparse
import re

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

try:
    import Image
except ImportError:
    logging.critical("This script requires the Python Imaging Library (PIL).")
    sys.exit(1)
try:
    import reportlab
except ImportError:
    logging.critical("Error: this script requires the reportlab package.")
    sys.exit(1)
    
from reportlab.lib import utils
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus.doctemplate import BaseDocTemplate
from reportlab.lib.units import inch
from reportlab.platypus import *
from reportlab.platypus.tableofcontents import TableOfContents
haikudoc=lambda x:x


#####################################################################################
# Configuration.
#####################################################################################
TITLE = "Skipper User Manual"
ROOT = "http://help.tryskipper.com"
EXCLUDED_URLS = r"^.*video.*$"
EXCLUDED_SECTIONS = ['Video Tutorials', 'All articles']

#####################################################################################
# Business Stuff
#####################################################################################
heading_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
relevant_tags = ['div','p','strong','ul','ol','li','img'] + heading_tags
styles = getSampleStyleSheet()

def print_tag(tag):
    if tag['tag'] == '_data':
        return '"'+tag['attrs']+'"'
    else:
        return "<"+tag['tag']+">"

def print_stack(stack):
    stack_string = "["
    for item in stack:
        stack_string += print_tag(item) + ","
    print repr(stack_string[:-1] + "]")


class PageParser(HTMLParser.HTMLParser):
    def __init__(self, story):
        HTMLParser.HTMLParser.__init__(self)
        self.story = story
        self.contentStarted = False
        self.stack = []
        self.insideIframe = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "section" and "uvFaq" in attrs['class']:
            self.contentStarted = True
            self.stack.append({"tag":tag, "attrs":attrs})
            return
        elif self.contentStarted == False or self.insideIframe == True:
            return
        elif tag in relevant_tags:
            self.stack.append({"tag":tag, "attrs":attrs})
        elif tag == "iframe":
            self.insideIframe = True
        else:
            pass

    def handle_data(self, data):
        if self.contentStarted and not self.insideIframe and re.match(r"^[\n ]*$", data) is None:
            self.stack.append({"tag":"_data", "attrs":data})

    def handle_endtag(self, tag):
        items = []

        if tag == "iframe":
            self.insideIframe = False
            return

        elif tag == "section":
            if not self.contentStarted:
                return
            self.contentStarted = False

        elif not self.contentStarted or tag not in relevant_tags or self.insideIframe:
            return

        while self.stack[-1]["tag"] != tag:
            items = [self.stack.pop(),] + items
        self.stack.pop()
        self.apply_tag(tag, items)

    def apply_tag(self, tag, items):
        for item in items:

            p = None
            if item['tag'] == "img":
                src = item['attrs'].get('src')

                # Walk back to the last paragraph and add a conditional page
                # break to keep this image on the same page as the preceding text
                lookback = []
                while self.story:
                    item = self.story.pop()
                    lookback.append(item)
                    if isinstance(item, Paragraph):
                        self.story.append(CondPageBreak(6*inch))
                        break
                self.story += reversed(lookback)

                w, h = utils.ImageReader(src).getSize()
                maxwidth = 250
                if w > maxwidth:
                    wpercent = (maxwidth/float(w))
                    h = int((float(h)*float(wpercent)))
                    w = maxwidth
                self.story.append(Spacer(0, 0.10*inch))
                self.story.append(Image(src, width=w, height=h))
                self.story.append(Spacer(0, 0.25*inch))

            elif item['tag'] == '_data':
                if tag == 'strong':
                    self.story.append(CondPageBreak(6*inch))
                    sty = styles['Heading4']
                elif tag == 'h1':
                    sty = styles['Heading2']
                else:
                    sty = styles['Normal']
                p = Paragraph(item['attrs'], sty)
            else:
                pass
            if p:
                self.story.append(p)

@haikudoc
class ContentParser(HTMLParser.HTMLParser):
    """
    Parses the main menu
    To call SubContentParser
    To parse submenus
    """
    def __init__(self, story):
        HTMLParser.HTMLParser.__init__(self)
        self.story = story
        self.insideHeading = False
        self.link = None

    def handle_starttag(self, tag, attrs):
        if tag == "h2":
            self.insideHeading = True
        attrs = dict(attrs)
        if self.insideHeading and tag == "a":
            self.link = attrs.get('href')

    def handle_data(self, data):
        if self.insideHeading:
            self.insideHeading = False
            if data in EXCLUDED_SECTIONS:
                self.link = None
            else:
                self.story.append(Paragraph(data, styles['Heading1']))

    def handle_endtag(self, tag):
        if tag == 'a' and self.link:
            parser = SubContentParser(self.story)
            html = urllib2.urlopen(ROOT + self.link).read().decode('utf8')
            parser.feed(html)
            parser.close()
            self.link = None

@haikudoc
class SubContentParser(HTMLParser.HTMLParser):
    """
    Parses submenus
    And calls crawl_page with the links
    Of actual pages
    """
    def __init__(self, story):
        HTMLParser.HTMLParser.__init__(self)
        self.insideHeading = False
        self.story = story

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h2" and attrs['class'] == 'uvListItemHeader':
            self.insideHeading = True
        elif tag == "a" and self.insideHeading:
            crawl_page(attrs['href'], self.story)
            self.insideHeading = False

@haikudoc
def crawl_page(url, story):
    """
    Crawls the knowledge base
    Appending elements to
    The PDF queue
    """
    if re.search(EXCLUDED_URLS, url):
        return

    print ("Crawling %s..." % url)

    url = ROOT + url

    page_parser = PageParser(story)
    html = urllib2.urlopen(url).read().decode('utf8')
    page_parser.feed(html)
    page_parser.close()
    story.append(PageBreak())


class WikiDocTemplate(BaseDocTemplate):

    def __init__(self, filename, **kwargs):
        BaseDocTemplate.__init__(self, filename, **kwargs)
        frame1 = Frame(self.leftMargin, self.bottomMargin, self.width/2-6, self.height, id='col1', leftPadding=0, rightPadding=10, showBoundary=0)
        frame2 = Frame(self.leftMargin+self.width/2+6, self.bottomMargin, self.width/2-6, self.height, id='col2', leftPadding=10, rightPadding=0, showBoundary=0)
        self.addPageTemplates([PageTemplate(id='TwoCol',frames=[frame1,frame2],onPage=self._do_footer),])

    def _do_footer(self, canvas,doc):
        canvas.saveState()
        canvas.setFont('Times-Roman', 10)
        canvas.setFont('Helvetica', 9)
        canvas.drawString(4*inch, 0.5*inch, "%d" % doc.page)
        canvas.restoreState()
        
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            text = flowable.getPlainText()
            style = flowable.style.name
            if style == "Heading1":
                self.notify('TOCEntry', (0, text, self.page))
                print " "
                print text
            elif style == "Heading2":
                self.notify('TOCEntry', (1, text, self.page))
                print "- >" + text


if __name__ == '__main__':
    doc = WikiDocTemplate("manual.pdf", leftMargin= 0.5*inch, rightMargin= 0.5*inch,
                     topMargin= 0.5*inch, bottomMargin= 0.25*inch)

    story = []

    # Title Page
    story.append(Spacer(0, 3.5*inch))
    story.append(Paragraph(TITLE, styles['Title']))
    story.append(PageBreak())

    # Table of Contents
    toc = TableOfContents()
    toc.levelStyles = [styles['Normal']] * 6
    story.append(toc)
    story.append(PageBreak())

    parser = ContentParser(story)
    html = urllib2.urlopen(ROOT + "/knowledgebase").read().decode('utf8')
    parser.feed(html)
    parser.close()

    # crawl_page("/knowledgebase/articles/171592-how-to-print-your-tracks", story)

    print story
    print "Building PDF..."
    
    # Build PDF

    doc.multiBuild(story)













