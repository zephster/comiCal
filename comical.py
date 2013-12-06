"""
comiCal - scrapes comic sites then imports release dates into google calendar
by brandon sachs
"""

import sys
import argparse
import requests
from bs4 import BeautifulSoup

""" 
relevant docs i may want to read:
    http://docs.python.org/2/library/queue.html
    http://docs.python.org/2/library/pickle.html
        https://wiki.python.org/moin/UsingPickle
     
css info paths
    for marvel
        iterate over the selector
            4 times - get latest 4? issues link urls. those selectors are just divs, newest to oldest
            go to each of those urls
                publish date selector: .featured-item-meta - need to parse out date
     
notes/ideas/whatever
    save/load list of comics
        can add sys opts to add/remove comics on-the-fly
            -a --add
                -p --publisher  string (dc|marvel|imagine else throw)
                -t --title      string (name of the comic)
                -u --uri        string
            -r --remove
                -p --publisher string (dc|marvel|imagine else throw)
                -t --title     string (when checking if it exists, normalize in lowercase or something, or use a case-insensitive flag if there is one)
 
    have an option to format comic title in uppercase or camel case?
        default to camel case?
        -f --format string (uppercase|camelcase else throw)

    have an option to indicate how many back-issues from the latest issue comical should check for release info
        -l --last   string (last? idunno)

    have an option in gcal to check if the comic exists already (for past issues) and to correct the date if its been updated
 
    when iterating through release_dates for gcal, if possible, search for the comic title first to see if it's already in the cal, then check the date of it. if the date is wrong, re-schedule to newer scraped date
"""

 
 
comic_base_urls = {
    "dc"                : "http://www.dccomics.com/comics/",
    "marvel"            : "http://marvel.com/comics/series/",
    "image"             : "http://www.imagecomics.com/comics/series/"
}

# these won't be hard-coded eventually
comics = {
    "dc" : {
        "Justice League"              : "justice-league-2011",
        "Superman"                    : "superman-2011",
        "Superman Unchained"          : "superman-unchained-2013",
        "Green Lantern"               : "green-lantern-2011",
        "Green Lantern Corps"         : "green-lantern-corps-2011",
        "Green Lantern New Guardians" : "green-lantern-new-guardians-2011"
    },
    "marvel" : {
        "Superior Spider-Man" : "17554/superior_spider-man_2013_-_present",
        "Ultimate Spider-Man" : "13831/ultimate_comics_spider-man_2011_-_present"
    },
    "image" : {
        "The Walking Dead" : "the-walking-dead"
    }
}
 
release_dates = {
    "dc"    : {},
    "marvel": {},
    "image" : {}
}
 
# the marvel selector will ignore issues that do not have their artworks posted yet
# they never have correct release info anyway
selectors = {
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

# make this an arg or somethin
marvel_get_last_issues = 4





# go! 
def main(argv):
    # for publisher, titles in comics.iteritems():
    #     if len(titles):
    #         for name, uri in titles.iteritems():
    #             scrape(publisher, name, uri)
    #     else:
    #         print "no titles to scrape in %s" % publisher
    
    
    # manually fetch one set for gcal testing
    # scrape("dc", "Superman", comics["dc"]["Superman"])
    # print release_dates
    
    
    # auth with google now!
    g_api = g_auth()
    
    if g_api != None:
        cal_present = g_check_comical_calendar(g_api)
        
        if cal_present != False:
            print "iterate through release dates and shit now!!!!!"
            
    else:
        print "not authed!"
    
    #keep open
    #raw_input()





# checks for the presence of the comiCal calendar. if not, create it.
# this is what comics will be labeled under
def g_check_comical_calendar(g_api_obj):
    print "checking for comiCal calendar..."
    cal_present = False
    
    try:
        calendar_list = g_api_obj.calendarList().list().execute()
        cals = calendar_list["items"]
        
        for cal in cals:
            if "comiCal" in cal.values():
                cal_present = True
                
        if not cal_present:
            return g_make_comical_calendar(g_api_obj)
    except Exception as e:
        print "error fetching google calendar list"
        print e
        
    return cal_present




def g_make_comical_calendar(g_api_obj):
    print "comiCal calendar not present, creating it..."
    cal_created = False
    
    try:
        comical = {
            "summary" : "comiCal"
        }
        create = g_api_obj.calendars().insert(body=comical).execute()
        
        if create != False:
            print "comiCal calendar created!"
            cal_created = True
    except Exception as e:
        print "error creating comiCal calendar"
        print e
    
    return cal_created




# https://developers.google.com/api-client-library/python/guide/aaa_oauth
# https://developers.google.com/api-client-library/python/start/get_started
def g_auth():
    import httplib2
    from apiclient import discovery
    from oauth2client import file
    from oauth2client import client
    from oauth2client import tools
    from oauth2client.client import OAuth2WebServerFlow
    
    flow = OAuth2WebServerFlow(scope         = google_oauth["scope"],
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
    
    # if auth credentials dont exist or are invalid, run flow (and save auth tokens)
    tokens      = file.Storage("comiCal_tokens.dat")
    credentials = tokens.get()
    
    if credentials is None or credentials.invalid:
      credentials = tools.run_flow(flow, tokens, flags)

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























"""
Scrape Marvel
"""
def scrape_marvel(comic_title, url):
    print "marvel - gathering info..."
    last_issues = {}

    try:
        r = requests.get(url)

        try:
            soup = BeautifulSoup(r.text.encode("utf-8"))

            count = 0
            for issue in soup.select(selectors["marvel_list"]):
                if count >= marvel_get_last_issues:
                    break
                issue_url = issue.get('href').strip()
                last_issues["%s #%s" % (comic_title, issue_url[-2:])] = issue_url
                count += 1

        except Exception as e:
            print "error parsing past issue url %s" % url
            print e

    except Exception as e:
        print "error gathering previous issue information"
        print e


    for title, url in last_issues.iteritems():
        print "marvel - getting release info for %s..." % title
        url = comic_base_urls["marvel"][:-15]+url

        try:
            r = requests.get(url)

            soup = BeautifulSoup(r.text.encode("utf-8"))

            for info in soup.select(selectors["marvel_release"]):
                info = info.text.strip().split("\n")
                date = info[0][11:]
                release_dates["marvel"][title] = date

        except Exception as e:
            print "unable to fetch issue info %s" % title
            print e




"""
Scrape Image and DC
"""
def scrape(publisher, comic_title, uri):
    url = comic_base_urls[publisher] + uri

    if publisher == "marvel":
        scrape_marvel(comic_title, url)
    else:
        print "%s - getting release info for %s..." % (publisher, comic_title)
        try:
            r = requests.get(url)
            
            try:
                soup = BeautifulSoup(r.text.encode("utf-8"))
                
                for issue in soup.select(selectors[publisher]):
                    issue = issue.text.strip()
                    issue = issue.split("\n")

                    try:
                        if publisher == "dc":
                            release_dates["dc"][issue[0].strip().title()] = issue[1][10:] # 10: strips "on sale" text
                            
                        elif publisher == "image":
                            release_dates["image"][issue[0]] = issue[1]
                            
                        else:
                            print "unsupported publisher"
                            
                    except Exception as e:
                        print "unable to find issue info on %s" % url
                        print e
                
            except Exception as e:
                print "unable to parse %s" % url
                print e
            
        except Exception as e:
            print "unable to fetch %s" % url
            print e













# init 
if __name__ == '__main__':
  main(sys.argv)
