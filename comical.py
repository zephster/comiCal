"""
comiCal - scrapes comic sites then imports release dates into google calendar
by brandon sachs
"""

import argparse
import requests
from bs4 import BeautifulSoup

from support.google import google_api
from support import util



class comiCal:
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
    
    release_dates = {}

    # filled in when created
    comiCal_calendar_id = None

    # make this an arg or somethin, see notes
    marvel_get_last_issues = 5

    # comic db file
    my_comics_file = "my_comics.pkl"

    def show_uri_info(self):
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

    def show_comics(self):
        try:
            comic_list = util.load_comics(self.my_comics_file)
        except IOError as e:
            print "no comics saved! add one using --add"
            exit()

        print "------------------------------"
        print "        comiCal comics        "
        print "------------------------------"

        for publisher, comics in comic_list.iteritems():
            print publisher
            
            for name, uri in comics.iteritems():
                print "-- %s (%s)" % (name, self.comic_base_urls[publisher] + uri)

    def add_comic(self, args):
        if not args.publisher:
            print "missing -p parameter (publisher)"
            exit()
        if not args.title:
            print "missing -t parameter (title)"
            exit()
        if not args.uri:
            print "missing -u parameter (uri)"
            exit()
        if args.publisher not in self.comic_base_urls.keys():
            print "unsupported publisher. please use one of the following:", self.comic_base_urls.keys()
            exit()
        
        print "verifying %s (%s)..." % (args.title.title(), self.comic_base_urls[args.publisher]+args.uri),
        self.scrape(args.publisher, args.title.title(), args.uri, verify=True)

        print "adding %s to comic list..." % args.title.title(),

        try:
            comics = util.load_comics(self.my_comics_file)
            comics[args.publisher][args.title.title()] = args.uri
        except Exception as e:
            # any exception here means there's no comics file opened.
            # so, create a blank comics object to use instead
            comics = {}
            for publisher in self.comic_base_urls.iterkeys():
                comics[publisher] = {}
            comics[args.publisher].update({args.title.title():args.uri})

        try:
            util.save_comics(self.my_comics_file, comics)
            print "ok"
        except Exception as e:
            print "error saving comics db"
            print e

    def remove_comic(self, args):
        if not args.publisher:
            print "missing -p parameter (publisher)"
            exit()
        if not args.title:
            print "missing -t parameter (title)"
            exit()
        
        print "removing %s %s from comic list..." % (args.publisher, args.title.title()),

        try:
            comics = util.load_comics(self.my_comics_file)
            del comics[args.publisher][args.title.title()]

            try:
                util.save_comics(self.my_comics_file, comics)
                print "ok"
            except Exception as e:
                print "error saving comics db"
                print e
        except KeyError as e:
            print "comic not found"
        except Exception as e:
            print "unknown exception removing comics"
            print e, type(e)

    def scan(self, args):
        # human centipede: first sequence
        print "------------------------------"
        print "      comiCal starting"
        print "------------------------------"

        # track stats
        class stats:
            adds, mods = 0, 0
        
        # load comics from saved. optionally parse args
        def load_comics(args):
            try:
                comics = util.load_comics(self.my_comics_file)
            except IOError as e:
                print "no comics found. please add a comic first"
                exit()
            except Exception as e:
                print "unknown exception opening saved comics"
                print type(e)
                exit()

            # args for scanning an individual comic
            if args.title and args.publisher:
                try:
                    comics = {
                        args.publisher: {
                            args.title : comics[args.publisher][args.title.title()]
                        }
                    }
                except KeyError as e:
                    print "comic '%s' not found for publisher '%s'. arguments are case-sensitive, try again." % (args.title, args.publisher)
                    print "use the --list command to view your comics"
                    exit()
                    
            elif args.title or args.publisher:
                print "error: you need both -t and -p arguments"
                exit()
                
            return comics
        
        # run the scapers
        def get_release_dates(comics):
            for publisher, titles in comics.iteritems():
                if len(titles):
                    for name, uri in titles.iteritems():
                        info = self.scrape(publisher, name, uri)
                        
                        try:
                            self.release_dates[publisher].update(info[publisher])
                        except KeyError as e:
                            self.release_dates[publisher] = {}
                            self.release_dates[publisher].update(info[publisher])
                            
            return self.release_dates
            
        # searches gcal for existing events, chooses to update or create event
        def process(release_dates):
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
                            stats.mods += 1
                        else:
                            print "error updating event :-("

                    elif search_result["action"] == "create":
                        print "adding %s on %s..." % (title, util.convert_date(publisher[0], date, "google")),

                        insert_status = g_api.calendar_event_create(title     = title,
                                                                    date      = date,
                                                                    publisher = publisher[0])
                        if insert_status:
                            print "ok" #" event_id: %s" % insert_status
                            stats.adds += 1
                        else:
                            print "error creating event :-("

                    elif search_result["action"] == None:
                        print "%s already in calendar on %s" % (title, search_result["date"])
                    else:
                        print "dunno wtf you just did"
        
        my_comics     = load_comics(args)
        release_dates = get_release_dates(my_comics)

        # auth with google now
        print "authenticating with google...",
        g_api = google_api()
        
        if g_api.auth():
            print "ok"
            cal_present = g_api.check_comical_calendar()
            
            if cal_present != False:
                process(release_dates)
        else:
            print "not authed!"
            
        print "\n------------------------------"
        print "      comiCal finished"
        print "%d new events, %d updated events" % (stats.adds, stats.mods)
        print "------------------------------"
        # todo: print stats here, like 1 additions, 2 modifications
        

    """
    Scrape Image and DC
    """
    def scrape(self, publisher, comic_title, uri, **args):
        url = self.comic_base_urls[publisher] + uri

        if publisher == "marvel":
            return self.scrape_marvel(comic_title, url, **args)
        else:
            if not args.get('verify'):
                print "%s - getting release info for %s..." % (publisher, comic_title.title()),
            
            try:
                r = requests.get(url, headers=self.request_headers)

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
                    
                    return_obj = {
                        publisher : {}
                    }
                    
                    for issue in soup.select(self.scrape_selectors[publisher]):
                        issue = issue.text.strip()
                        issue = issue.split("\n")

                        try:
                            if publisher == "dc":
                                return_obj[publisher][issue[0].strip().title()] = issue[1][10:]
                                
                            elif publisher == "image":
                                return_obj[publisher][issue[0]] = issue[1]
                                
                        except Exception as e:
                            print "unable to find issue info on %s" % url
                            print type(e)

                    print "ok"
                    return return_obj
                    
                except Exception as e:
                    print "unable to parse %s" % url
                    print e
                
            except Exception as e:
                print "unable to fetch %s" % url
                print e
                
        
    """
    Scrape Marvel
    """
    def scrape_marvel(self, comic_title, url, **args):
        def get_latest_issues(url, **args):
            if not args.get('verify'):
                print "marvel - getting resources for %s..." % comic_title.title(),
                
            last_issues = {}
            try:
                r = requests.get(url, headers=self.request_headers)

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

                    count = 0
                    for issue in soup.select(self.scrape_selectors["marvel_list"]):
                        if count >= self.marvel_get_last_issues:
                            break
                        issue_url = issue.get('href').strip()

                        try:
                            issue_num = int(issue_url[-2:])
                        except ValueError:
                            # some issues have periods in them (eg. 18.1, 18.2)
                            if issue_url[-2:][0] == ".":
                                issue_num = issue_url[-4:]
                            else:
                                issue_num = issue_url[-2:][1]

                        last_issues["%s #%s" % (comic_title, issue_num)] = issue_url
                        count += 1

                    print "ok"
                    return last_issues

                except Exception as e:
                    print "error parsing past issue url %s" % url
                    print e
                    exit()

            except Exception as e:
                print "error gathering previous issue information"
                print e
                exit()
            
        
        def get_issue_info(last_issues, verifying):
            return_obj = {
                "marvel": {}
            }

            if not verifying:
                for title, url in last_issues.iteritems():
                    print "marvel - getting release info for %s..." % title.title(),
                    url = self.comic_base_urls["marvel"][:-15]+url

                    try:
                        r = requests.get(url, headers=self.request_headers)

                        if r.status_code == 404:
                            print "error: url %s not found" % url
                            exit()

                        soup = BeautifulSoup(r.text.encode("utf-8"))

                        for info in soup.select(self.scrape_selectors["marvel_release"]):
                            info = info.text.strip().split("\n")
                            date = info[0][11:]
                            return_obj["marvel"][title] = date
                            print "ok"

                    except Exception as e:
                        print "unable to fetch issue info %s" % title
                        print e
                        exit()
                        
                return return_obj
                    
        last_issues = get_latest_issues(url, **args)
        return get_issue_info(last_issues, args.get('verify'))
    


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
    
    c = comiCal()

    if args.list:
        c.show_comics()
    elif args.info:
        c.show_uri_info()
    elif args.add:
        c.add_comic(args)
    elif args.remove:
        c.remove_comic(args)
    elif args.scan:
        # hold on to your butts!
        c.scan(args)
    else:
        print "use the --help command"
    exit()




# init 
if __name__ == '__main__':
  main()