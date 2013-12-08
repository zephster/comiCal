"""
comiCal - scrapes comic sites then imports release dates into google calendar
by brandon sachs
"""

import argparse
import requests
from time import strptime, strftime
from bs4 import BeautifulSoup



# a publisher is officially supported once added here
comic_base_urls = {
    "dc"                : "http://www.dccomics.com/comics/",
    "marvel"            : "http://marvel.com/comics/series/",
    "image"             : "http://www.imagecomics.com/comics/series/"
}

date_format = {
    "dc"    : "%b %d %Y",
    "image" : "%B %d, %Y",
    "marvel": "%B %d, %Y",
    "google": "%Y-%m-%d"
}
 
scrape_selectors = {
    "dc"            : ".row-1 td",
    "marvel_list"   : ".JCMultiRow-comic_issue > .comic-item .row-item-image a.row-item-image-url",
    "marvel_release": ".featured-item-meta",
    "image"         : ".latest_releases .release_box"
}

google_oauth = {
    "scope"         : "https://www.googleapis.com/auth/calendar", # no trailing /
    "client_id"     : "488080564532-iqr034it5tp32raunksro01bap1op3oi.apps.googleusercontent.com",
    "client_secret" : "SRv6OZtPGK7_VvowZFN2LxWa",
    "redirect_uris" : ["urn:ietf:wg:oauth:2.0:oob","oob"]
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




def comiCal_convert_date(publisher, date, target):
    date = strptime(date, date_format[publisher])
    date = strftime(date_format[target], date)
    return date

def comiCal_load_comics(file):
    import cPickle as pickle
    p = pickle.load(open(file, "rb"))
    return p

def comiCal_save_comics(file, comics_obj):
    import cPickle as pickle
    p = pickle.dump(comics_obj, open(file, "wb"))
    return p

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
        comic_list = comiCal_load_comics(my_comics_file)
    except IOError as e:
        "could not find %s" % my_comics_file

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
        comics = comiCal_load_comics(my_comics_file)
        comics[args.publisher][args.title] = args.uri
    except Exception as e:
        # any exception here means there's no comics file opened.
        # so, create a blank comics object to use instead
        comics = {}
        for publisher in comic_base_urls.iterkeys():
            comics[publisher] = {}
        comics[args.publisher].update({args.title:args.uri})

    try:
        comiCal_save_comics(my_comics_file, comics)
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
        comics = comiCal_load_comics(my_comics_file)
        del comics[args.publisher][args.title]

        try:
            comiCal_save_comics(my_comics_file, comics)
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

    try:
        my_comics = comiCal_load_comics(my_comics_file)
    except IOError as e:
        print "no comics found. please add a comic first"
        exit()
    except Exception as e:
        print "unknown exception opening saved comics"
        print e

    if args.title and args.publisher:
        my_comics = {
            args.publisher: {
                args.title : my_comics[args.publisher][args.title]
            }
        }

    for publisher, titles in my_comics.iteritems():
        if len(titles):
            for name, uri in titles.iteritems():
                scrape(publisher, name, uri)
        else:
            print "no titles to scrape in %s" % publisher
    
    # auth with google now
    print "authenticating with google...",
    g_api = g_auth()
    
    if g_api != None:
        print "ok"
        cal_present = g_check_comical_calendar(g_api)
        
        if cal_present != False:
            for publisher in release_dates.iteritems():
                for comic in publisher[1].iteritems():
                    title         = comic[0]
                    date          = comic[1]
                    search_result = g_search(g_api, publisher[0], title, date)

                    if search_result["action"] == "update":
                        print title + " already in calendar, but on an incorrect date. updating...",

                        update_status = g_update_event_date(g_api,
                                                            event_id = search_result["event_id"],
                                                            new_date = search_result["new_date"])
                        if update_status:
                            print "ok. new date: %s" % update_status["new_date"]
                        else:
                            print "error updating event :-("

                    elif search_result["action"] == "create":
                        print "%s added on %s..." % (title, comiCal_convert_date(publisher[0], date, "google")),

                        insert_status = g_create_event(g_api,
                                                       title     = title,
                                                       date      = date,
                                                       publisher = publisher[0])
                        if insert_status:
                            print "ok"#" event_id: %s" % insert_status
                        else:
                            print "error creating event :-("


                    elif search_result["action"] == None:
                        print "%s already in calendar on %s" % (title, search_result["date"])
                    else:
                        print "dunno wtf you just did"
            
    else:
        print "not authed!"
    
    #keep open
    #raw_input()










"""
Scrape Marvel
"""
def scrape_marvel(comic_title, url):
    global release_dates
    print "marvel - gathering info...",
    last_issues = {}

    try:
        r = requests.get(url)

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
            r = requests.get(url)

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
        if not args["verify"]:
            print "%s - getting release info for %s..." % (publisher, comic_title),
        
        try:
            r = requests.get(url)

            if r.status_code == 404:
                if not args["verify"]:
                    print "error: url %s not found" % url
                else:
                    print "url not found"
                exit()
            else:
                if args["verify"]:
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








def g_create_event(g_api_obj, **info):
    date = comiCal_convert_date(info["publisher"], info["date"], "google")

    event = {
      "summary": info["title"],
      "description" : "added by comiCal.py",
      "start": {
        "date" : date
      },
      "end": {
        "date" : date
      }
    }
    
    created_event = g_api_obj.events().insert(calendarId=comiCal_calendar_id, body=event).execute()
    return created_event['id']

def g_update_event_date(g_api_obj, **info):
    # get current event and change some stuff
    event                  = g_api_obj.events().get(calendarId=comiCal_calendar_id, eventId=info["event_id"]).execute()
    event["end"]["date"]   = u"%s" % info["new_date"]
    event["start"]["date"] = u"%s" % info["new_date"]
    updated_event          = g_api_obj.events().update(calendarId=comiCal_calendar_id, eventId=info["event_id"], body=event).execute()

    if updated_event:
        return {
            "new_date" : info["new_date"]
        }
    else:
        return False

# searches for comic issue to see if its already on the calendar.
def g_search(g_api_obj, publisher, title, latest_release_date):
    try:
        latest_release_date_gcal = comiCal_convert_date(publisher, latest_release_date, "google")
        results = g_api_obj.events().list(calendarId=comiCal_calendar_id,
                                          q=title).execute()

        # ensure correct event
        result = None
        for found in results["items"]:
            if title == found["summary"]:
                result = found
                break
        
        result_title = result["summary"]
        result_date  = result["start"]['date']

        if result != None and latest_release_date_gcal != result_date:
            return {
                "action"  : "update",
                "new_date": latest_release_date_gcal,
                "event_id": result["id"]
                }
        else:
            return {
                "action": None,
                "date"  : result_date
            }
    except (IndexError, TypeError) as e:
        return {
            "action": "create",
            "title" : title,
            "date"  : latest_release_date_gcal
        }
        return e
    except Exception as e:
        print "unknown exception in g_search"
        print e

# checks for the presence of the comiCal calendar. if not, create it.
def g_check_comical_calendar(g_api_obj):
    global comiCal_calendar_id
    print "checking for comiCal calendar...",
    cal_present = False
    
    try:
        calendar_list = g_api_obj.calendarList().list().execute()
        cals = calendar_list["items"]
        
        for cal in cals:
            if "comiCal" in cal.values():
                cal_present = True
                comiCal_calendar_id = cal["id"]
                
        if not cal_present:
            return g_create_comical_calendar(g_api_obj)
    except Exception as e:
        print "error fetching google calendar list"
        print e
    
    print "ok"    
    return cal_present

def g_create_comical_calendar(g_api_obj):
    global comiCal_calendar_id
    print "comiCal calendar not present, creating it..."
    cal_created = False
    
    try:
        comical = {
            "summary" : "comiCal"
        }
        create = g_api_obj.calendars().insert(body=comical).execute()
        comiCal_calendar_id = create["id"]
        
        if create != False:
            print "comiCal calendar created!"
            cal_created = True
    except Exception as e:
        print "error creating comiCal calendar"
        print e
    
    return cal_created

def g_auth():
    import httplib2
    from apiclient import discovery
    from oauth2client import file
    from oauth2client import client
    from oauth2client import tools
    from oauth2client.client import OAuth2WebServerFlow
    
    flo_rida = OAuth2WebServerFlow(scope         = google_oauth["scope"],
                                   client_id     = google_oauth["client_id"],
                                   client_secret = google_oauth["client_secret"],
                                   redirect_uris = google_oauth["redirect_uris"])
    
    flags = {
        "auth_host_name"         : 'localhost',
        "auth_host_port"         : [8080, 8090],
        "logging_level"          : 'ERROR',
        "noauth_local_webserver" : False
    }
    flags = argparse.Namespace(**flags)
    
    # if auth credentials dont exist or are invalid, run flo_rida (and save auth tokens)
    tokens      = file.Storage("comiCal_tokens.dat")
    credentials = tokens.get()
    
    if credentials is None or credentials.invalid:
      credentials = tools.run_flow(flo_rida, tokens, flags)

    # httplib2 object to handle requests with correct auth creds
    http = httplib2.Http()
    http = credentials.authorize(http)

    # service object for using calendar api
    # g_api = discovery.build('calendar', 'v3', http=http)

    try:
        return discovery.build('calendar', 'v3', http=http)
    except client.AccessTokenRefreshError:
        print ("The credentials have been revoked or expired, please re-run the application to re-authorize")
        return False






# init 
if __name__ == '__main__':
  main()
