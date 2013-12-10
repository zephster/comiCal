# comiCal

comic release dates right in your google calendar!
by brandon sachs


## required modules
these are available using pip
- requests
- beautifulsoup4
- google-api-python-client

## how do i use this?
- [register an app on google](https://cloud.google.com/console)

- plug your OAuth info into support/google.py

- add a comic
```
comical.py --add -p publisher -t title -u uri
```

- uri?
```
comical.py --info
```

- remove a comic
```
comical.py --remove -p publisher -t title
```

- view your comics
```
comical.py --list
```

- scan and import all comics
```
comical.py --scan
```

- scan and import a single comic
```
comical.py --scan -p publisher -t title
```

after gathering release info, comiCal will launch a browser window prompting you to log in, and to allow comiCal calendar access.

comiCal creates a new calendar called "comiCal" to prevent cluttering your main calendar.


## notes
- argument values are case-sensitive; superman is not Superman
- if you need to update a uri, you don't have to remove then re-add the comic; just re-add it, and it will overwrite the old value.