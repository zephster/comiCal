"""
comiCal - scrapes comic sites then imports release dates into google calendar
by brandon sachs
"""

import argparse
import requests
from bs4 import BeautifulSoup

from support.google import google_api
from support import util


# a publisher is officially supported once added here
comic_base_urls = {
    "dc"                : "http://www.dccomics.com/comics/",
    "marvel"            : "http://marvel.com/comics/series/",
    "image"             : "http://www.imagecomics.com/comics/series/"
}
 
scrape_selectors = {
    "dc"            : ".row-1 td",
    "marvel_list"   : ".JCMultiRow-comic_issue > .comic-item .row-item-image a.row-item-image-url",
    "marvel_release": ".featured-item-meta",
    "image"         : ".latest_releases .release_box"
}

request_headers = {
    "User-Agent" : "comiCal"
}

release_dates = {
    "dc"    :{},
    "marvel":{},
    "image" :{}
}

# filled in when created
comiCal_calendar_id = None

# make this an arg or somethin, see notes
marvel_get_last_issues = 5

# comic db file
my_comics_file = "my_comics.pkl"


def main():
    parser = argparse.ArgumentParser("comiCal.py")
    parser.add_argument('-l', '--list',   action ='store_true', help='lists all of your comics')
    parser.add_argument('-i', '--info',   action ='store_true', help='info on --uri, and how to find it yours')
    parser.add_argument('-a', '--add',    action ='store_true', help='add a comic to your list. use -t, -p, and -u')
    parser.add_argument('-s', '--scan',   action ='store_true', help='checks comics. blank for all, -t and -p for specific')
    parser.add_argument('-r', '--remove', action ='store_true', help='remove a comic from your list. use -t and -p')
    parser.add_argument('-u', '--uri')
    parser.add_argument('-t', '--title')
    parser.add_argument('-p', '--publisher')
    args = parser.parse_args()

    if args.list:
        comiCal_show_comics()
    elif args.info:
        comiCal_show_uri_info()
    elif args.add:
        comiCal_add_comic(args)
    elif args.remove:
        comiCal_remove_comic(args)
    elif args.scan:
        # hold on to your butts!
        comiCal_scan(args)
    else:
        print "use the --help command"
    exit()

def comiCal_show_uri_info():
    print "--------------comiCal----------"
    print "comiCal requires the uri segments for supported publishers"
    print "examples:"
    print "\tdc:"
    print "\t\thttp://www.dccomics.com/comics/superman-2011"
    print "\t\turi: superman-2011"
    print "\tmarvel:"
    print "\t\thttp://marvel.com/comics/series/17554/superior_spider-man_2013_-_present"
    print "\t\turi: 17554/superior_spider-man_2013_-_present"
    print "\timage:"
    print "\t\thttp://www.imagecomics.com/comics/series/the-walking-dead"
    print "\t\turi: the-walking-dead"

def comiCal_show_comics():
    try:
        comic_list = util.load_comics(my_comics_file)
    except IOError as e:
        "could not find %s" % my_comics_file

    print "------------------------------"
    print "        comiCal comics        "
    print "------------------------------"

    for publisher, comics in comic_list.iteritems():
        print publisher
        
        for name, uri in comics.iteritems():
            print "-- %s (%s)" % (name, comic_base_urls[publisher] + uri)

def comiCal_add_comic(args):
    if not args.publisher:
        print "missing -p parameter (publisher)"
        exit()
    if not args.title:
        print "missing -t parameter (title)"
        exit()
    if not args.uri:
        print "missing -u parameter (uri)"
        exit()
    if args.publisher not in comic_base_urls.keys():
        print "unsupported publisher. please use one of the following:", comic_base_urls.keys()
        exit()
    
    print "verifying %s (%s)..." % (args.title, comic_base_urls[args.publisher]+args.uri),
    scrape(args.publisher, args.title, args.uri, verify=True)

    print "adding %s (%s) to comic list..." % (args.title, comic_base_urls[args.publisher]+args.uri),

    try:
        comics = util.load_comics(my_comics_file)
        comics[args.publisher][args.title] = args.uri
    except Exception as e:
        # any exception here means there's no comics file opened.
        # so, create a blank comics object to use instead
        comics = {}
        for publisher in comic_base_urls.iterkeys():
            comics[publisher] = {}
        comics[args.publisher].update({args.title:args.uri})

    try:
        util.save_comics(my_comics_file, comics)
        print "ok"
    except Exception as e:
        print "error saving comics db"
        print e

def comiCal_remove_comic(args):
    if not args.publisher:
        print "missing -p parameter (publisher)"
        exit()
    if not args.title:
        print "missing -t parameter (title)"
        exit()
    
    print "removing %s %s from comic list..." % (args.publisher, args.title),

    try:
        comics = util.load_comics(my_comics_file)
        del comics[args.publisher][args.title]

        try:
            util.save_comics(my_comics_file, comics)
            print "ok"
        except Exception as e:
            print "error saving comics db"
            print e
    except KeyError as e:
        print "comic title is case-sensitive!"
    except Exception as e:
        print "unknown exception removing comics"
        print e, type(e)

def comiCal_scan(args):
    # human centipede: first sequence
    print "------------------------------"
    print "      comiCal starting!"
    print "------------------------------"

    # load comics
    try:
        my_comics = util.load_comics(my_comics_file)
    except IOError as e:
        print "no comics found. please add a comic first"
        exit()
    except Exception as e:
        print "unknown exception opening saved comics"
        print e

    # args for scanning an individual comic
    if args.title and args.publisher:
        try:
            my_comics = {
                args.publisher: {
                    args.title : my_comics[args.publisher][args.title]
                }
            }
        except KeyError as e:
            print "comic '%s' not found for publisher '%s'. arguments are case-sensitive, try again." % (args.title, args.publisher)
            print "use the --list command to view your comics"
            exit()
    elif args.title or args.publisher:
        print "error: you need both -t and -p arguments"
        exit()


    # scan selected
    for publisher, titles in my_comics.iteritems():
        if len(titles):
            for name, uri in titles.iteritems():
                scrape(publisher, name, uri)
        else:
            print "no titles to scrape in %s" % publisher
    

    # auth with google now
    print "authenticating with google...",
    g_api = google_api()
    
    if g_api.auth():
        print "ok"
        cal_present = g_api.check_comical_calendar()
        
        if cal_present != False:
            for publisher in release_dates.iteritems():
                for comic in publisher[1].iteritems():
                    title         = comic[0]
                    date          = comic[1]
                    search_result = g_api.calendar_search(publisher[0], title, date)

                    if search_result["action"] == "update":
                        print title + " already in calendar, but on an incorrect date. updating...",

                        update_status = g_api.calendar_event_update_date(event_id = search_result["event_id"],
                                                                         new_date = search_result["new_date"])
                        if update_status:
                            print "ok. new date: %s" % update_status["new_date"]
                        else:
                            print "error updating event :-("

                    elif search_result["action"] == "create":
                        print "adding %s on %s..." % (title, util.convert_date(publisher[0], date, "google")),

                        insert_status = g_api.calendar_event_create(title     = title,
                                                                    date      = date,
                                                                    publisher = publisher[0])
                        if insert_status:
                            print "ok" #" event_id: %s" % insert_status
                        else:
                            print "error creating event :-("

                    elif search_result["action"] == None:
                        print "%s already in calendar on %s" % (title, search_result["date"])
                    else:
                        print "dunno wtf you just did"
    else:
        print "not authed!"


"""
Scrape Marvel
"""
def scrape_marvel(comic_title, url):
    global release_dates
    print "marvel - getting resources for %s" % comic_title,
    last_issues = {}

    try:
        r = requests.get(url, headers=request_headers)

        if r.status_code == 404:
            print "error: url %s not found" % url
            exit()

        try:
            soup = BeautifulSoup(r.text.encode("utf-8"))

            count = 0
            for issue in soup.select(scrape_selectors["marvel_list"]):
                if count >= marvel_get_last_issues:
                    break
                issue_url = issue.get('href').strip()
                last_issues["%s #%s" % (comic_title, issue_url[-2:])] = issue_url
                count += 1

            print "ok"

        except Exception as e:
            print "error parsing past issue url %s" % url
            print e

    except Exception as e:
        print "error gathering previous issue information"
        print e



    for title, url in last_issues.iteritems():
        print "marvel - getting release info for %s..." % title,
        url = comic_base_urls["marvel"][:-15]+url

        try:
            r = requests.get(url, headers=request_headers)

            if r.status_code == 404:
                print "error: url %s not found" % url
                exit()

            soup = BeautifulSoup(r.text.encode("utf-8"))

            for info in soup.select(scrape_selectors["marvel_release"]):
                info = info.text.strip().split("\n")
                date = info[0][11:]
                release_dates["marvel"][title] = date
                print "ok"

        except Exception as e:
            print "unable to fetch issue info %s" % title
            print e

"""
Scrape Image and DC
"""
def scrape(publisher, comic_title, uri, **args):
    global release_dates
    url = comic_base_urls[publisher] + uri

    if publisher == "marvel":
        scrape_marvel(comic_title, url)
    else:
        if not args.get('verify'):
            print "%s - getting release info for %s..." % (publisher, comic_title),
        
        try:
            r = requests.get(url, headers=request_headers)

            if r.status_code == 404:
                if not args.get('verify'):
                    print "error: url %s not found" % url
                else:
                    print "url not found"
                exit()
            else:
                if args.get('verify'):
                    print "ok"
                    return
            
            try:
                soup = BeautifulSoup(r.text.encode("utf-8"))
                
                for issue in soup.select(scrape_selectors[publisher]):
                    issue = issue.text.strip()
                    issue = issue.split("\n")

                    try:
                        if publisher == "dc":
                            release_dates["dc"][issue[0].strip().title()] = issue[1][10:] # 10: strips "on sale" text
                            
                        elif publisher == "image":
                            release_dates["image"][issue[0]] = issue[1]
                            
                    except Exception as e:
                        print "unable to find issue info on %s" % url
                        print e

                print "ok"
                
            except Exception as e:
                print "unable to parse %s" % url
                print e
            
        except Exception as e:
            print "unable to fetch %s" % url
            print e



# init 
if __name__ == '__main__':
  main()