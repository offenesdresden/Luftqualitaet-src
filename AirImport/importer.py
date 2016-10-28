#!/usr/bin/env python3

import attr

import os, datetime
import logging, traceback
log = logging.getLogger('uws')

from io import StringIO
import requests
from bs4 import BeautifulSoup

try:
    from . import UmweltSachsen as uws
except:
    import UmweltSachsen as uws

def is_safe_path(basedir, path, follow_symlinks=True):
    # resolves symbolic links
    if follow_symlinks:
        return os.path.realpath(path).startswith(basedir)
    return os.path.abspath(path).startswith(basedir)

@attr.s
class Substance(object):
    id = attr.ib()
    name = attr.ib()
    station = attr.ib()
    accuracy = attr.ib(default = None)

@attr.s
class Station(object):
    id = attr.ib()
    name = attr.ib()
    substances = attr.ib(default = attr.Factory(list))

@attr.s
class LuftOnlineSiteConfig(object):
    stations = attr.ib(default = attr.Factory(list))

    _session = attr.ib(default = attr.Factory(requests.Session))
    _post_data = attr.ib(default = attr.Factory(dict))

    station = attr.ib(default = None)
    substance = attr.ib(default =  None)
    
    basedir = attr.ib(default = attr.Factory(lambda: os.getcwd))
    
    out_dir = attr.ib(default = attr.Factory(lambda: '.'))

    def get_live_data(self, periods = [(2016, 9)]):
        self.read_stations()
        for period in periods:
            for station in self.stations:
                self.load_substances(station)
                for substance in station.substances:
                    self.set_period(period)
                    self.load_substance_data(substance)
                    self.get_csv_data()

    def read_stations(self):
        # Make a first page load, it contains the stations
        log.info('Read stations')
        soup = self._get_string()
        # Cleanup
        for i in self.stations:
            i.substances.clear()
        self.stations.clear()
        # Do add stations
        stations = soup.find(id = uws.STATIONS_ID)
        for i in stations.find_all('option'):
            self.stations.append(Station(name = i.string, id = i['value']))
        
    def load_substances(self, station):
        # Set up all stations
        log.info("Processing station %s", station.name)
        self._post_data[uws.TARGET] = uws.STATIONS_KEY
        self._post_data[uws.STATIONS_KEY] = station.id
        soup = self._get_string()

        self.station = station.name

        # Cleanup
        station.substances.clear()
        # Get substances
        log.debug('Selected station, getting substances')
        substances = soup.find(id=uws.SUBSTANCES_ID)
        for i in substances.find_all('option'):
            station.substances.append(
                Substance(station = station, name = i.string, id = i['value']))

    def set_period(self, period = (2016, 9)):
        def s(n):
            return '0' * (2 - len(str(n))) + str(n)
        year, month = period
        date = datetime.datetime(year = year, month = month, day = 1)
        month_delta = datetime.timedelta(days = 31)
        end_date = date + month_delta
        self.year, self.month = s(date.year), s(date.month)
        self.end_year, self.end_month = s(end_date.year), s(end_date.month)

    def load_substance_data(self, substance):
        # Set substance
        log.info("Processing substance %s", substance.name)
        self._post_data[uws.TARGET] = uws.SUBSTANCES_KEY
        self._post_data[uws.SUBSTANCES_KEY] = substance.id
        soup = self._get_string()

        self.substance = substance

        # Select best accuracy possible (hourly, daily, monthly)
        accuracies = [x['value'] for x in
            soup.find(id=uws.AVERAGE_ID).find_all('option')]
        for acc in uws.ACCURACY:
            if acc in accuracies:
                substance.accuracy = acc
                break

        self._post_data[uws.TARGET] = uws.AVERAGE_KEY
        self._post_data[uws.AVERAGE_KEY] = substance.accuracy
        log.debug('Setting average to: %s', substance.accuracy)
        self._get_string()
        
        self._post_data[uws.TARGET] = uws.TIME_KEY
        self._post_data.update(dict(uws.set_time_params(
            (self.year, self.month), (self.end_year, self.end_month))))

        log.debug('Setting time limits: %s-%s', self.month, self.year)
        self._get_string()
        
    def get_csv_data(self):
        self._post_data[uws.BUTTON] = uws.BUTTON_VALUE
        
        self._post_data[uws.TARGET] = ''
        log.info('Downloading data...')
        dir_path = '{}/{}/{}'.format(self.out_dir, self.year, self.month)
        file = '{},{}'.format(self.substance.station.name, self.substance.name)
        file = os.path.join(dir_path, file)
        if not is_safe_path(self.basedir, file):
            log.error('*** Directory traversal attack: %s\n%s',
                file, self.substance)
            return

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        try:
            data = self._get_string(raw = True).replace(
                'n. def.', '').replace(',', '.').replace(
                    '; ', separator)
            del self._post_data[uws.BUTTON]
            ext = 'csv' if data[0] != '<' else 'html'
            with open('{}.{}'.format(file, ext), 'w') as f:
                f.write(data)
        except:
            log.warning('*** Error downloading %s', self.substance)
            with open('{}.{}'.format(file, 'err'), 'w') as f:
                f.write(traceback.format_exc())

    def _get_string(self, raw = False):
        response = self._session.post(uws.URL, self._post_data, timeout = 45)
        response.raise_for_status()
        if raw:
            return response.text
        soup = BeautifulSoup(response.text, 'html.parser')
        for vd in (uws.VALIDATION, uws.VIEWSTATE, uws.VIEWSTATEGEN,
                '__SCROLLPOSITIONX', '__SCROLLPOSITIONY',
                '__EVENTARGUMENT', '__LASTFOCUS'):
            el = soup.find(id = vd)
            if el is not None:
                self._post_data[vd] = el['value']
        return soup


def main(date = '09-2016', end_date = None, out_dir = '.',
        basedir = os.getcwd()):
    if end_date is None:
        end_date = date
    start = [int(i) for i in date.split('-')]
    end = [int(i) for i in end_date.split('-')]
    def periods():
        periods = []
        for year in range(start[1], end[1] + 1):
            for month in range(
                    1 if year != start[1] else start[0],
                    (12 if year != end[1] else end[0]) + 1):
                yield (year, month)
    h = LuftOnlineSiteConfig(out_dir = out_dir, basedir = basedir)
    h.get_live_data(periods())

separator = ','
if __name__ == '__main__':
    from logging import StreamHandler
    import sys
    stdout_logger = StreamHandler(sys.stdout)
    stderr_logger = StreamHandler(sys.stderr)
    log.addHandler(stdout_logger)
    log.addHandler(stderr_logger)
    stdout_logger.setLevel(logging.INFO)
    stderr_logger.setLevel(logging.ERROR)

    from optparse import OptionParser
    class OptParser(OptionParser):
        def format_epilog(self, formatter):
            return self.epilog
    parser = OptParser(epilog = u"""
This script deals with data from 
http://www.umwelt.sachsen.de/umwelt/infosysteme/luftonline/recherche.aspx

Output data is basically raw, only modifications are:
* Decimal symbol is a point
* Missing data are empty fields instead of 'n. def.'
* Separator is set to --separator instead of '; ' (defaults to ',')

Without arguments it will download data for September 2016 as a test. This is
equivalent to a call with --date 09-2016.

Call it with --date MM-YYYY and optionally --end-date MM-YYYY to download the
given interval (both months included). If --end-date is not passed, only the
month given in --date will be downloaded.

File separator can be specified with --separator SEPARATOR, it defaults to ','.
""")
    parser.add_option(
        "-d", "--date",
        dest = "date",
        default = "09-2016",
        help = u"Start date for the download in format MM-YYYY",
    )
    parser.add_option(
        "-e", "--end-date",
        dest = "end_date",
        default = None,
        help = u"".join([
            u"End date for the download in format MM-YYYY, ",
            u"this month will be included. ",
            u"If not passed, only --date will be downloaded",
        ])
    )
    parser.add_option(
        "-o", "--out-dir",
        dest = "out_dir",
        default = ".",
        help = u"Directory to save the downloaded files to."
    )
    parser.add_option(
        "-s", "--separator",
        dest = "separator",
        default = separator,
        help = u"Separator for the csv",
    )
  
    (options, arguments) = parser.parse_args()
    separator = options.separator
    main(options.date, options.end_date, options.out_dir)
