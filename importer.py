"""
comic importer - scrapes comic sites then imports release dates into google calendar
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
 
selectors = {
    "dc"     : ".row-1 td",
    "marvel" : ".JCMultiRow-comic_issue > .comic-item", # untested, see notes
    "image"  : ".latest_releases .release_box"
}
 
 
 
def main():
    # manual dc test
    if len(comics["dc"]):
        scrape_dc("Green Lantern", comics["dc"]["Green Lantern"])
    
    # manual marvel test
    # if len(comics["marvel"]):
    #     scrape_marvel("Superior Spider-Man", comics["marvel"]["Superior Spider-Man"])
    
    # manual image test
    if len(comics["image"]):
        scrape_image("The Walking Dead", comics["image"]["The Walking Dead"])
    
    
    
    
    
    # if len(comics["dc"]):
    #     for title, url in comics["dc"].iteritems():
    #         scrape_dc(title, url)
    
    # if len(comics["marvel"]): 
    #     for title, url in comics["marvel"].iteritems():
    #         scrape_marvel(title, url)
    
    # if len(comics["image"]):
    #     for title, url in comics["image"].iteritems():
    #         scrape_image(title, url)
     
    print release_dates
     
     
# scrape imagecomics.com
def scrape_image(comic_title, uri):
    url = base_url["image"] + uri
    print "scraping %s" % url
    
    try:
        r = requests.get(url)
        
        try:
            soup = BeautifulSoup(r.text.encode("utf-8"))
            
            for issue in soup.select(selectors["image"]):
                info = issue.text.strip()
                info = info.split("\n")
                release_dates["image"][info[0]] = info[1]
            
        except Exception as e:
            print "error parsing %s" % url
            print e
            
    except Exception as e:
        print "error fetching %s" % url
        print e
 
 
# scrape marvel.com
def scrape_marvel(comic_title, uri):
    pass
 
     
# scrape dccomics.com
def scrape_dc(comic_title, uri):
    url = base_url["dc"] + uri
    print "scraping %s" % url
     
    try:
        r = requests.get(url)
 
        try:
            soup = BeautifulSoup(r.text.encode("utf-8"))
             
            for issue in soup.select(selectors["dc"]):
                issue = issue.text.strip()
                issue = issue.split("\n")
                release_dates["dc"][issue[0].strip()] = issue[1][10:] # 10: strips "on sale" text
             
        except Exception as e:
            print "error parsing %s" % url
            print e
         
    except Exception as e:
        print "error fetching %s" % url
        print e
 
 
 
 
     
     
     
     
     
     
 
 
if __name__ == '__main__':
  main()