#!/usr/bin/env python3

# Data source: Umwelt Sachsen
URL = 'http://www.umwelt.sachsen.de/umwelt/infosysteme/luftonline/recherche.aspx'

TARGET = '__EVENTTARGET'
VALIDATION = '__EVENTVALIDATION'
VIEWSTATE = '__VIEWSTATE'
VIEWSTATEGEN = '__VIEWSTATEGENERATOR'
BUTTON = 'ctl00$Inhalt$BtnCsvDown'
BUTTON_VALUE = 'CSV-Download'

AVERAGE_ID = 'ctl00_Inhalt_MwttList'
AVERAGE_KEY = 'ctl00$Inhalt$MwttList'
STATIONS_ID = 'ctl00_Inhalt_StationList'
STATIONS_KEY = 'ctl00$Inhalt$StationList'
SUBSTANCES_ID  = 'ctl00_Inhalt_SchadstoffList'
SUBSTANCES_KEY  = 'ctl00$Inhalt$SchadstoffList'
TIME_KEY = 'ctl00$Inhalt$LetzteList'

ACCURACY = [
    '45; 3600', # hours
    '21; 86400', # days
    '177; 1', # months
]

def set_time_params(start, end):
    return [
        ('ctl00$Inhalt$LetzteList', 0),
        ('ctl00$Inhalt$AZTag', '01'),
        ('ctl00$Inhalt$AZMonat', start[1]),
        ('ctl00$Inhalt$AZJahr', start[0]),
        ('ctl00$Inhalt$EZTag', '01'),
        ('ctl00$Inhalt$EZMonat', end[1]),
        ('ctl00$Inhalt$EZJahr', end[0]),
        ('ctl00$Inhalt$DiagrammOpt', 'Linie'),
    ]
