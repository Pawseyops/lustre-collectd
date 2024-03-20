#!/usr/bin/python3.9

# Script to spit out lustre stats towards an influxdb server
# Andrew Elwell <Andrew.Elwell@pawsey.org.au>, Sept 2017. Available under GPL2+
# Hints from http://wiki.lustre.org/Lustre_Monitoring_and_Statistics_Guide

import requests
import os
import socket
import time
import subprocess
import daemon

# which nutter enabled auth on influx
username = 'FIXME'
password = 'FIXME'
url = 'https://influx.example.com:8086'

hostname = socket.gethostname()

debug = True

def grabbit():
    post = ''

    # Overall OST space
    ts = int(time.time()*1000000000)
    stats = subprocess.check_output(["lctl","get_param", "obdfilter.*OST*.kbytes*"]).decode('UTF-8').splitlines()
    space = {}
    for stat in stats:
        keys,val = stat.split("=")
        _, OST, metric = keys.split(".", 2)
        fs,ost = OST.split("-")
        space[metric] = val
    foo = ','.join([f'{key}={value}' for key, value in space.items()])
    post += f'usage,fs={fs},ost={ost} {foo} {ts}\n'

    # Operations per OST. Read and write data is particularly interesting
    # returns multivalue with sample timestamp
    stats = subprocess.check_output(["lctl","get_param", "obdfilter.*.stats"]).decode('UTF-8').splitlines()
    fields = []
    for line in stats:
        if line.endswith("stats="):
             fs,ost = line.split(".", 2)[1].split("-")
             tmp = f'usage,fs={fs},ost={ost}'
             if fields == []:
                 prefix = tmp
             else:
                 post += f'{prefix} {",".join(fields)} {ts}\n'
                 fields = []
                 prefix = tmp
                 tmp = ''
        elif "_bytes" in line:
            k,count,null,null,min_size,max_size,sum_bytes,sum_sqared = line.split()
            fields.append(f'{k}={sum_bytes}')
        else:
             k,v,null = line.split(None,2)
             if k == "snapshot_time":
                 ts=v.replace('.','')
             elif '_time' in k:
                 continue
             #else:
             #    print('IGNORED', line)
    post += f'{prefix} {",".join(fields)} {ts}\n'

   # we may as well grab loadavg at the same time
    load1,load5,load15 = os.getloadavg()
    post += f'loadavg,fs={fs},host={hostname} load1={load1},load5={load5},load15={load15} {ts}\n'


    #print(post)
    p = requests.post(url+'/write?db=lustre',data=post, auth=(username, password))
    #print(p.status_code, p.text)




if debug:
    grabbit()

else:
    with daemon.DaemonContext():
        while True:
            try:
                grabbit()
            except:
                import sys
                sys.exit("Whoa, that went a bit Pete Tong!")
            time.sleep(10)
