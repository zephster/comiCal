"""
comiCal - scrapes comic sites then imports release dates into google calendar
by brandon sachs
"""

import sys
import argparse
import requests
from time import strptime, strftime
from bs4 import BeautifulSoup

""" 
relevant docs:
    https://developers.google.com/google-apps/calendar/v3/reference/
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

# filled in when created
comiCal_calendar_id = None

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
    
    
    # # manually fetch one set for gcal testing
    # scrape("dc", "Superman", comics["dc"]["Superman"])
    # print release_dates
    
    # temp
    # release_dates = {'image': {u'The Walking Dead #116': u'November 13, 2013',u'The Walking Dead #117': u'November 27, 2013'}, 'dc': {u'Green Lantern Corps #28': u'Feb 12 2014',u'Green Lantern Corps #25': u'Nov 13 2013',u'Green Lantern Corps #26': u'Dec 11 2013',u'Green Lantern Corps #27': u'Jan 15 2014',u'Superman Unchained #4': u'Nov 6 2013',u'Superman Unchained #5': u'Dec 31 2013',u'Superman Unchained #6': u'Jan 29 2014',u'Superman Unchained #7': u'Feb 26 2014',u'Green Lantern #25': u'Nov 6 2013',u'Green Lantern #27': u'Jan 8 2014',u'Green Lantern #26': u'Dec 4 2013',u'Justice League #28': u'Feb 19 2014',u'Green Lantern: New Guardians #26': u'Dec 18 2013',u'Green Lantern: New Guardians #27': u'Jan 22 2014',u'Superman #28': u'Feb 26 2014',u'Green Lantern: New Guardians #25': u'Nov 20 2013',u'Superman #26': u'Dec 31 2013',u'Superman #27': u'Jan 29 2014',u'Green Lantern: New Guardians #28': u'Feb 19 2014',u'Superman #25': u'Nov 27 2013',u'Justice League #25': u'Dec 11 2013',u'Justice League #27': u'Jan 22 2014',u'Justice League #26': u'Dec 24 2013',u'Green Lantern/Red Lanterns #28': u'Feb 5 2014'}, 'marvel': {u'Ultimate Spider-Man #27': u'September 25, 2013',u'Ultimate Spider-Man #26': u'August 28, 2013',u'Ultimate Spider-Man #28': u'October 23, 2013',u'Ultimate Spider-Man #32': u'February 19, 2014',u'Superior Spider-Man #25': u'January 15, 2014',u'Superior Spider-Man #27': u'February 12, 2014',u'Superior Spider-Man #26': u'January 29, 2014',u'Superior Spider-Man #28': u'February 26, 2014'}}
    
    # auth with google now!
    g_api = g_auth()
    
    if g_api != None:
        cal_present = g_check_comical_calendar(g_api)
        
        if cal_present != False:
            # iterate through release_dates and use g_search to see if there are already issues present in the calendar
            # this way, if there is already the comic issue on the calendar, and the date differs from the latest release date
            #   update that found event instead of creating a new one. recycling kicks ass.
            print "searching comiCal calendar for a manual entry Superman #26"
            result = g_search(g_api, "Superman #26", "Dec 31 2013")
            print "search results: %s" % result

            if result["action"] == "update":
                print "run g_update_event function"
                update_status = g_update_event_date(g_api, result["event_id"], result["new_date"])
                if update_status:
                    print "successfully updated event to latest release date"

            elif result["action"] == "create":
                # i need the users email for this, minimum
                print "run g_create_event function"

            elif result["action"] == None:
                print "there is already a calendar entry for this comic, on the correct date. continue"
            else:
                print "dunno wtf you just did"
            
    else:
        print "not authed!"
    
    #keep open
    #raw_input()





def g_create_event(g_api_obj, title, date):
    # https://developers.google.com/google-apps/calendar/v3/reference/events/insert
    pass

def g_update_event_date(g_api_obj, event_id, new_date):
    # get current event and change some stuff
    event                  = g_api_obj.events().get(calendarId=comiCal_calendar_id, eventId=event_id).execute()
    event["end"]["date"]   = u"%s" % new_date
    event["start"]["date"] = u"%s" % new_date
    updated_event          = g_api_obj.events().update(calendarId=comiCal_calendar_id, eventId=event_id, body=event).execute()

    if updated_event:
        return True
    else:
        return False



date_format = {
    "dc"    : "%b %d %Y",
    "image" : "%B %d, %Y",
    "marvel": "%B %d, %Y",
    "google":"%Y-%m-%d"
}


# searches for comic issue to see if its already on the calendar.
def g_search(g_api_obj, title, latest_release_date):
    global comiCal_calendar_id # temp? dunno
    try:
        # normalize dates between publishers, compare to latest
        print "DEBUG g_search - latest_release_date_gcal strptime using hard-coded dc comics date format"
        latest_release_date_gcal = strptime(latest_release_date, date_format["dc"])
        latest_release_date_gcal = strftime(date_format["google"], latest_release_date_gcal)

        print "temporary manually setting calendar id"
        comiCal_calendar_id = "jebkd11hv062j2u2s47rku0vt0@group.calendar.google.com"

        print "comiCal calendar id: %s" % comiCal_calendar_id
        results = g_api_obj.events().list(calendarId=comiCal_calendar_id,
                                          q=title).execute()
        
        result_title = results["items"][0]["summary"]
        result_date  = results["items"][0]["start"]['date']

        if latest_release_date_gcal != result_date:
            return {
                "action" : "update",
                "new_date" : latest_release_date_gcal,
                "event_id" : results["items"][0]["id"]
                }
        else:
            return {
                "action" : None
            }
    except IndexError as e:
        return {
            "action" : "create",
            "date" : latest_release_date_gcal
        }
        return e
    except Exception as e:
        print "unknown exception in g_search"
        return e





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
                comiCal_calendar_id = cal["id"]
                
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
        comiCal_calendar_id = create["id"]
        
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
