"""
comiCal util.py
"""
from time import strftime, strptime
import cPickle as pickle

# convert date formats between publishers/google
date_format = {
    "dc"    : "%b %d %Y",
    "image" : "%B %d, %Y",
    "marvel": "%B %d, %Y",
    "google": "%Y-%m-%d"
}
def convert_date(publisher, date, target):
    date = strptime(date, date_format[publisher])
    date = strftime(date_format[target], date)
    return date

# load comics from file
def load_comics(file):
    p = pickle.load(open(file, "rb"))
    return p

# save comics_obj to file
def save_comics(file, comics_obj):
    p = pickle.dump(comics_obj, open(file, "wb"))
    return p