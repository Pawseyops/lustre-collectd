#!/usr/bin/python3.9

# Script to spit out lustre stats towards an influxdb server
# Andrew Elwell <Andrew.Elwell@pawsey.org.au>, Sept 2017. Available under GPL2+
# Hints from http://wiki.lustre.org/Lustre_Monitoring_and_Statistics_Guide

import requests    # makes life much easier with newer neo
import time        # changelog_users doesn't have snapshot time
import subprocess
import re
import os
import socket
import daemon


debug = True

# which nutter enabled auth on influx
username = 'FIXME'
password = 'FIXME'
url = 'https://influx.example.com:8086'

hostname = socket.gethostname()

def grabbit():
    fs=''
    mdt=''
    ts=0
    post = ''
    measurement=''
    fields = []
    # Do we have one or more MDTs mounted?
    mdtstats = subprocess.check_output(['lctl','get_param', 'mdt.*.md_stats']).splitlines()
    tmp = ''
    prefix = ''
    for line in mdtstats:
        line = line.decode('UTF-8')
        if '=' in line:
            x = re.search('mdt.(.*).md_stats', str(line))
            fs,mdt = x.group(1).split("-")
            tmp =f'metadata,fs={fs},mdt={mdt},host={hostname}'
            if fields == []:
               prefix = tmp
            else:
                #print('NEW BLOCK', fields, prefix)
                measurement += '{} {} {}\n'.format(prefix,','.join(fields), ts)
                fields = []
                prefix = tmp
                tmp = ''
        else:
          key,val,null = line.split(None,2)
          if key == "snapshot_time":
            ts=val.replace('.','') # mmmm. nanosecond accuracy on metrics.
          elif '_time' in key:
              continue
          else:
              fields.append('{}={}'.format(key,int(val))) #
    if fields != []:
       measurement += '{} {} {}\n'.format(prefix,','.join(fields), ts)

    # are there any changelogs?
    tmp = ''
    clstats = subprocess.check_output(['lctl','get_param', 'mdd.*.changelog_users']).splitlines()
    ts = int(time.time()*1000000000)
    for line in clstats:
        line = line.decode('UTF-8')
        if 'users=' in line:
           if tmp  != '': # we've come to a new header
               if fields != []:
                   measurement += '{} {} {}\n'.format(prefix,','.join(fields), ts)
           x = re.search('mdd.(.*).changelog_users', line)
           fs,mdt = x.group(1).split("-")
           fields = []
        elif 'current_index' in line:
            fields.append('head={}'.format(line.split()[1]))
        elif 'ID' in line:
            prefix = 'changelog,fs={},mdt={}'.format(fs,mdt)
            tmp = prefix
        else:
          key,val,idle = line.split()
          fields.append('{}={}'.format(key,val))
    if fields != []:
       measurement += '{} {} {}\n'.format(prefix,','.join(fields), ts)


    # total files & free (on MDT)
    mdtstats = subprocess.check_output(["lctl","get_param", "osd-*.*MDT*.files*"]).splitlines()
    ts = int(time.time()*1000000000)
    for stat in mdtstats:
        stat = stat.decode('UTF-8')
        keys,val = stat.split('=')
        _, mds, metric = keys.split('.', 2)
        fs,mdt = mds.split('-')

        measurement += 'usage,fs={},mdt={} {}={} {}\n'.format(fs,mdt,metric,val,ts)
        # yes this sucks. I should really have one measurement with total,free,used timestamp

    # we may as well grab loadavg at the same time
    load1,load5,load15 = os.getloadavg()
    measurement += f'loadavg,fs={fs},host={hostname} load1={load1},load5={load5},load15={load15} {ts}\n'



    if debug:
       print(measurement)
    return measurement

if debug:
    post = grabbit()
    p = requests.post(url+'/write?db=lustre',data=post, auth=(username, password))
    print(p.status_code)
else:
    with daemon.DaemonContext():
      while True:
        try:
          post = grabbit()
          p = requests.post(url+'/write?db=lustre',data=post, auth=(username, password))
        except:
          import sys
          sys.exit("Whoa, that went a bit Pete Tong!")
        time.sleep(10)

