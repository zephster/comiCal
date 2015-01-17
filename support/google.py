"""
comiCal google.py
"""
import util


class google_api:
	g_api_obj           = None
	comiCal_calendar_id = None

	# https://cloud.google.com/console
	# you need to register your own app
	oauth = {
	    "scope"         : "https://www.googleapis.com/auth/calendar",
	    "client_id"     : "",
	    "client_secret" : "",
	    "redirect_uris" : ["urn:ietf:wg:oauth:2.0:oob","oob"]
	}
	
	def __init__(self):
		if not self.oauth["client_id"] or not self.oauth["client_secret"]:
			print "invalid oauth credentials"
			exit()


	# checks for the presence of the comiCal calendar. if not, creates it using create_comical_calendar
	def check_comical_calendar(self):
	    print "checking for comiCal calendar...",
	    cal_present = False
	    
	    try:
	        calendar_list = self.g_api_obj.calendarList().list().execute()
	        cals = calendar_list["items"]
	        
	        for cal in cals:
	            if "comiCal" in cal.values():
	                cal_present = True
	                self.comiCal_calendar_id = cal["id"]
	                
	        if not cal_present:
	            print "comiCal calendar not present. creating it...",
	            return self.create_comical_calendar()
	    except Exception as e:
	        print "error fetching google calendar list"
	        print "message: ", e
	        exit()
	    
	    print "ok"    
	    return cal_present

	# creates the comiCal calendar
	def create_comical_calendar(self):
	    cal_created = False
	    
	    try:
	        comical = {
	            "summary" : "comiCal"
	        }
	        create = self.g_api_obj.calendars().insert(body=comical).execute()
	        self.comiCal_calendar_id = create["id"]
	        
	        if create != False:
	            print "ok"
	            cal_created = True
	    except Exception as e:
	        print "error creating comiCal calendar"
	        print e
	    
	    return cal_created

	# searches for comic issue to see if its already on the calendar
	def calendar_search(self, publisher, title, latest_release_date):
	    try:
	        latest_release_date_gcal = util.convert_date(publisher, latest_release_date, "google")
	        results = self.g_api_obj.events().list(calendarId=self.comiCal_calendar_id,
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
	        print "unknown exception in calendar_search"
	        print e

    # update a calendar event's date
	def calendar_event_update_date(self, **info):
	    event         = self.g_api_obj.events().get(calendarId=self.comiCal_calendar_id, eventId=info["event_id"]).execute()
	    event["end"]["date"]   = u"%s" % info["new_date"]
	    event["start"]["date"] = u"%s" % info["new_date"]
	    updated_event = self.g_api_obj.events().update(calendarId=self.comiCal_calendar_id, eventId=info["event_id"], body=event).execute()

	    if updated_event:
	        return {
	            "new_date" : info["new_date"]
	        }
	    else:
	        return False

	# create a calendar event
	def calendar_event_create(self, **info):
		date = util.convert_date(info["publisher"], info["date"], "google")

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
		
		created_event = self.g_api_obj.events().insert(calendarId=self.comiCal_calendar_id, body=event).execute()
		return created_event['id']

	# authenticate with google
	def auth(self):
		import argparse
		import httplib2
		from apiclient import discovery
		from oauth2client import file
		from oauth2client import client
		from oauth2client import tools
		from oauth2client.client import OAuth2WebServerFlow
		
		flo_rida = OAuth2WebServerFlow(scope         = self.oauth["scope"],
		                               client_id     = self.oauth["client_id"],
		                               client_secret = self.oauth["client_secret"],
		                               redirect_uris = self.oauth["redirect_uris"])
		
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

		try:
			self.g_api_obj = discovery.build('calendar', 'v3', http=http)
			return True
		except client.AccessTokenRefreshError:
		    print ("The credentials have been revoked or expired, please re-run the application to re-authorize")
		    return False