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
    http://stackoverflow.com/questions/16618240/how-to-add-parameters-to-a-built-file-in-sublime-text-3-before-execution
    http://docs.python.org/2/library/queue.html
     
notes/ideas/whatever
    save/load list of comics
        can add sys opts to add/remove comics on-the-fly
            -a --add (run scrape and gcal routines, add info to comics pickle)
                -p --publisher  string (dc|marvel|imagine else throw)
                -t --title      string (name of the comic)
                -u --uri        string
            -r --remove (unpickle comics, search if title exists, if so, remove, re-pickle)
                -p --publisher string (dc|marvel|imagine else throw)
                -t --title     string (when checking if it exists, normalize in lowercase or something, or use a case-insensitive flag if there is one)
 
    have an option to format comic title in uppercase or camel case?
        default to camel case?
        -f --format string (uppercase|camelcase else throw)

    have an option to indicate how many back-issues from the latest issue comical should check for release info
        -l --last   string (last? idunno)
        marvel will be the easiest to implement this with since all their issues are lumped up into one element lol

    have an option to specify just one comic to scan and update from your saved comics list
"""



"""
    known bug - when running from nothing (no comiCal calendar created), green lantern 25/26/27 are UPDATED to their release date instead of being CREATED as an entirely new event. the newly created calendar should be empty, so this is strange. just those 3 comics. wtf?
"""


 
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



# temp cached release_dates
# release_dates = {'image': {u'The Walking Dead #116': u'November 13, 2013',u'The Walking Dead #117': u'November 27, 2013'}, 'dc': {u'Green Lantern Corps #28': u'Feb 12 2014',u'Green Lantern Corps #25': u'Nov 13 2013',u'Green Lantern Corps #26': u'Dec 11 2013',u'Green Lantern Corps #27': u'Jan 15 2014',u'Superman Unchained #4': u'Nov 6 2013',u'Superman Unchained #5': u'Dec 31 2013',u'Superman Unchained #6': u'Jan 29 2014',u'Superman Unchained #7': u'Feb 26 2014',u'Green Lantern #25': u'Nov 6 2013',u'Green Lantern #27': u'Jan 8 2014',u'Green Lantern #26': u'Dec 4 2013',u'Justice League #28': u'Feb 19 2014',u'Green Lantern: New Guardians #26': u'Dec 18 2013',u'Green Lantern: New Guardians #27': u'Jan 22 2014',u'Superman #28': u'Feb 26 2014',u'Green Lantern: New Guardians #25': u'Nov 20 2013',u'Superman #26': u'Dec 31 2013',u'Superman #27': u'Jan 29 2014',u'Green Lantern: New Guardians #28': u'Feb 19 2014',u'Superman #25': u'Nov 27 2013',u'Justice League #25': u'Dec 11 2013',u'Justice League #27': u'Jan 22 2014',u'Justice League #26': u'Dec 24 2013',u'Green Lantern/Red Lanterns #28': u'Feb 5 2014'}, 'marvel': {u'Ultimate Spider-Man #27': u'September 25, 2013',u'Ultimate Spider-Man #26': u'August 28, 2013',u'Ultimate Spider-Man #28': u'October 23, 2013',u'Ultimate Spider-Man #32': u'February 19, 2014',u'Superior Spider-Man #25': u'January 15, 2014',u'Superior Spider-Man #27': u'February 12, 2014',u'Superior Spider-Man #26': u'January 29, 2014',u'Superior Spider-Man #28': u'February 26, 2014'}}




# converts the various date formats publishers use on their websites
def convert_date(publisher, date, target):
    date = strptime(date, date_format[publisher])
    date = strftime(date_format[target], date)
    return date

def load_comics(file):
    import cPickle as pickle
    p = pickle.load(open(file, "rb"))
    return p

def save_comics(file, comics_obj):
    import cPickle as pickle
    p = pickle.dump(comics_obj, open(file, "wb"))
    return p






def main(argv):
    try:
        my_comics = load_comics("comics.pkl")
    except IOError as e:
        print "no comics found. please add a comic first"
        exit()
    except Exception as e:
        print "unknown exception opening saved comics"
        print e


    # hold on to your butts
    for publisher, titles in my_comics.iteritems():
        if len(titles):
            for name, uri in titles.iteritems():
                scrape(publisher, name, uri)
        else:
            print "no titles to scrape in %s" % publisher

    
    # auth with google now
    print "authenticating with google..."
    g_api = g_auth()
    
    if g_api != None:
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
                        print "%s added on %s..." % (title, convert_date(publisher[0], date, "google")),

                        insert_status = g_create_event(g_api,
                                                       title = title,
                                                       date = date,
                                                       publisher = publisher[0])
                        if insert_status:
                            print "ok. event_id: %s" % insert_status
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





def g_create_event(g_api_obj, **info):
    date = convert_date(info["publisher"], info["date"], "google")

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
        latest_release_date_gcal = convert_date(publisher, latest_release_date, "google")
        results = g_api_obj.events().list(calendarId=comiCal_calendar_id,
                                          q=title).execute()
        
        result_title = results["items"][0]["summary"]
        result_date  = results["items"][0]["start"]['date']

        if latest_release_date_gcal != result_date:
            # print "---------------------"
            # print title + " being updated, wtf?"
            # print "latest_release_date_gcal " + latest_release_date_gcal
            # print "result date " + result_date
            # print results
            # print "---------------------"

            return {
                "action"  : "update",
                "new_date": latest_release_date_gcal,
                "event_id": results["items"][0]["id"]
                }
        else:
            return {
                "action": None,
                "date"  : result_date
            }
    except IndexError as e:
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
# this is what comics will be labeled under
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
            return g_make_comical_calendar(g_api_obj)
    except Exception as e:
        print "error fetching google calendar list"
        print e
    
    print "ok"    
    return cal_present




def g_make_comical_calendar(g_api_obj):
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
    global release_dates
    print "marvel - gathering info...",
    last_issues = {}

    try:
        r = requests.get(url)

        try:
            soup = BeautifulSoup(r.text.encode("utf-8"))

            count = 0
            for issue in soup.select(scrape_selectors["marvel_list"]):
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


    print "ok"

    for title, url in last_issues.iteritems():
        print "marvel - getting release info for %s..." % title,
        url = comic_base_urls["marvel"][:-15]+url

        try:
            r = requests.get(url)

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
def scrape(publisher, comic_title, uri):
    global release_dates
    url = comic_base_urls[publisher] + uri

    if publisher == "marvel":
        scrape_marvel(comic_title, url)
    else:
        print "%s - getting release info for %s..." % (publisher, comic_title),
        try:
            r = requests.get(url)
            
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
                            
                        else:
                            print "unsupported publisher"
                            
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
  main(sys.argv)
