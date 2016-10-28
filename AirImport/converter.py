#!/usr/bin/env python3

import attr

import os
import logging
log = logging.getLogger('uws')

from io import StringIO
import requests

try:
    from . import UmweltSachsen as uws
except:
    import UmweltSachsen as uws

def is_safe_path(basedir, path, follow_symlinks=True):
    # resolves symbolic links
    if follow_symlinks:
        return os.path.realpath(path).startswith(basedir)
    return os.path.abspath(path).startswith(basedir)

separator = ','

@attr.s
class CityData(object):
    name = attr.ib()
    substances = attr.ib(default = attr.Factory(list))
    units = attr.ib(default = attr.Factory(list))
    data = attr.ib(default = attr.Factory(dict))

@attr.s
class Conversor(object):
    cities = attr.ib(default = attr.Factory(dict))
    substances = attr.ib(default = attr.Factory(set))

    basedir = attr.ib(default = attr.Factory(os.getcwd))
    out_dir = attr.ib(default = attr.Factory(lambda: 'data'))
    
    def convert_csv_part(self, buf):
        cities = self.cities
        # Since this script deals with both csv from Umwelt Sachsen
        # and data from the importer, we need to autodetect the file separator
        file_separator = ';'
        header = buf.readline()
        if len(header.split(file_separator)) == 1:
            file_separator = ','
        # Get headers (City names, substances, units)
        header = header.split(file_separator)
        units_row = buf.readline().split(file_separator)
        city_names = [
            ' '.join(txt.split(' ')[:-1]).strip() for txt in header[1:]]
        substances = [txt.split(' ')[-1].strip() for txt in header[1:]]
        units = [txt.strip() for txt in units_row[1:]]
        # Ensure there is a CityData entry for each city
        for city in city_names:
            if not cities.get(city, False):
                cities[city] = CityData(name = city)
        # Parse data
        for l in buf:
            l = l.replace('n. def.', '')
            l = [txt.strip() for txt in l.split(file_separator)]
            # Take care of monthly generated data as it appears "09-2016"
            if len(l[0]) < 8:
                l[0] = '01-{}-{}'.format(l[0][:2],l[0][5:])
            # Format to YYYY-MM-DD
            time = '-'.join(['20' + l[0][6:8], l[0][3:5], l[0][:2]]) + l[0][8:]
              
            for city, substance, us, v in zip(
                    city_names, substances, units, l[1:]):
                # Ignore points without data
                if not v:
                    continue
                # Ensure substance has been added
                if substance not in cities[city].substances:
                    cities[city].substances.append(substance)
                    self.substances.add((substance, us))
                    cities[city].units.append(us)
                    cities[city].data[substance] = dict()
                # Add value
                cities[city].data[substance][time] = v.replace(',', '.')
    
    def write_csv(self, city):
        # Ensure file is in writable path
        file = '{}/{}.csv'.format(self.out_dir, city.name)
        if not is_safe_path(self.basedir, file):
            log.error('*** Directory traversal attack: %s\n%s',
                file, city.name)
            return

        f = open('{}/{}.csv'.format(self.out_dir, city.name), 'w')
 
        substances = sorted(self.substances)

        # Write headers
        f.write(separator.join(['Datum', 'Zeit'] +
            [s[0] for s in substances]).strip() + '\n')
        # And units line
        f.write(separator.join(['yyyy-mm-dd', 'hh:mm'] +
            [s[1] for s in substances]).strip() + '\n')
        # Get all timepoints used for this city
        timepoints = set()
        for y in [city.data[x].keys() for x in city.substances]:
            timepoints = timepoints.union(y)
        timepoints = sorted(timepoints)
        # Write data
        for t in timepoints:
            vs = [city.data.get(s[0], dict()).get(t, '') for s in substances]
            # Take care of daily/montly generated data (no hh::mm)
            ts = t.split(' ') if len(t.split(' ')) == 2 else [t, '']
            f.write(separator.join(ts + vs) + '\n')
        f.close()
    
    def convert_csv(self, str_data = None, filenames = None):
        if str_data is not None:
            data = data.split('Datum Zeit')
            for part in str_data:
                self.convert_csv_part(StringIO(part))
        if filenames is not None:
            for filename in filenames:
                self.convert_csv_part(open(filename, 'r'))
            
        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir)
        with open('{}/_cities.csv'.format(self.out_dir), 'w') as f:
            for c in sorted(self.cities.values()):
                self.write_csv(c)
                f.write(c.name + '\n')

def main(filename = None, data_dir = None, out_dir = 'data',
        basedir = os.getcwd()):
    if filename is not None:
        return Conversor(
            out_dir = out_dir, basedir = basedir).convert_csv(
                str_data = open(filename, 'r').read())
    if data_dir is not None:
        files = [os.path.join(data_dir, f) for f in os.listdir(data_dir)
            if os.path.isfile(os.path.join(data_dir, f))]
        return Conversor(
            out_dir = out_dir, basedir = basedir).convert_csv(
                filenames = files)

if __name__ == '__main__':
    from logging.handlers import RotatingFileHandler
    file_logger = RotatingFileHandler('importer.log')
    log.setLevel(logging.DEBUG)
    log.addHandler(file_logger)

    from optparse import OptionParser
    class OptParser(OptionParser):
        def format_epilog(self, formatter):
            return self.epilog
    parser = OptParser(epilog = u"""
This script deals with data from 
http://www.umwelt.sachsen.de/umwelt/infosysteme/luftonline/recherche.aspx

Call it with --file FILE, where FILE has been manually downloaded from Umwelt
Sachsen, it generates developer friendlier CSV files in the data subdirectory.

File separator can be specified with --separator SEPARATOR, it defaults to ','.
""")
 
    parser.add_option(
        "-f", "--file",
        dest = "filename",
        help = u"CSV file to read data from",
    )
    parser.add_option(
        "-o", "--out-dir",
        dest = "out_dir",
        default = "data",
        help = u"Directory to save modified files to."
    )
    parser.add_option(
        "-d", "--data-dir",
        dest = "data_dir",
        default = "data",
        help = u"Directory to save modified files to."
    )
 
    parser.add_option(
        "-s", "--separator",
        dest = "separator",
        default = separator,
        help = u"Separator for the csv",
    )
  
    (options, arguments) = parser.parse_args()
    separator = options.separator
    if (not options.filename or not os.path.exists(options.filename)) and\
            (not options.data_dir or not os.path.exists(options.data_dir)):
        parser.error(u'Call with either --file FILE.csv or --data-dir DIR')
        
    if options.filename:
        main(filename = options.filename, out_dir = options.out_dir)
    else:
        main(data_dir = options.data_dir, out_dir = options.out_dir)
        
