# comiCal

comic release dates right in your google calendar!
by brandon sachs


## required modules
these are available using pip
- requests
- beautifulsoup4
- google-api-python-client

## how do i use this?
add a comic
```
--add -p publisher -t title -u uri
```

uri? huh?
```
--info
```

remove a comic
```
--remove -p publisher -t title
```

view your comics
```
--list
```

scan and import all comics
```
--scan
```

scan and import a single comic
```
--scan -p publisher -t title
```

##### comiCal uses oAuth2 to authenticate with your google account
after gathering release info, comiCal will launch a browser window prompting you to log in, and to allow comiCal calendar access.

comiCal creates a new calendar called "comiCal" to prevent cluttering your main calendar.


## notes
- argument values are case-sensitive; superman is not Superman
- if you need to update a uri, you don't have to remove then re-add the comic; just re-add it, and it will overwrite the old value.