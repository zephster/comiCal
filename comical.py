"""
comiCal - scrapes comic sites then imports release dates into google calendar
by brandon sachs
"""
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
    use cPickle to save/load list of comics
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
 
 

 
 
base_url = {
    "dc"    : "http://www.dccomics.com/comics/",
    "marvel": "http://marvel.com/comics/series/",
    "image" : "http://www.imagecomics.com/comics/series/"
}
 
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
# they never have correct release info
selectors = {
    "dc"            : ".row-1 td",
    "marvel_list"   : ".JCMultiRow-comic_issue > .comic-item .row-item-image a.row-item-image-url",
    "marvel_release": ".featured-item-meta",
    "image"         : ".latest_releases .release_box"
}

# make this an arg or somethin
marvel_get_last_issues = 4
 
 
 
def main():
    for publisher, titles in comics.iteritems():
        if len(titles):
            for name, uri in titles.iteritems():
                scrape(publisher, name, uri)
        else:
            print "no titles to scrape in %s" % publisher
    
    print release_dates



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
        print "marvel - getting release info for %s" % title
        url = base_url["marvel"][:-15]+url

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





def scrape(publisher, comic_title, uri):
    url = base_url[publisher] + uri

    if publisher == "marvel":
        scrape_marvel(comic_title, url)
    else:
        print "%s - getting release info for %s" % (publisher, comic_title)
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
  main()
