#!/usr/bin/python

# Script to spit out lustre stats towards an influxdb server
# Andrew Elwell <Andrew.Elwell@pawsey.org.au>, Sept 2017. Available under GPL2+
# Hints from http://wiki.lustre.org/Lustre_Monitoring_and_Statistics_Guide

import urllib2
import time
import subprocess
import daemon

# which nutter enabled auth on influx
username = 'FIXME'
password = 'FIXME'
url = "https://influx.example.com:8086"
pw = urllib2.HTTPPasswordMgr()
pw.add_password("InfluxDB", url, username, password)
handler = urllib2.HTTPBasicAuthHandler(pw)
opener = urllib2.build_opener(handler)
urllib2.install_opener(opener)



def grabbit():
    post = ""

    # Overall OST space
    ts = int(time.time()*1000000)
    stats = subprocess.check_output(["lctl","get_param", "obdfilter.*OST*.kbytes*"]).splitlines()
    for stat in stats:
        keys,val = stat.split("=")
        _, OST, metric = keys.split(".", 2)
        fs,ost = OST.split("-")
        post += 'usage,fs={0},ost={1} {3}={4}i {5}\n'.format(fs,ost,OST,metric,val,ts)

    # Operations per OST. Read and write data is particularly interesting
    # returns multivalue with sample timestamp
    stats = subprocess.check_output(["lctl","get_param", "obdfilter.*.stats"]).splitlines()
    for line in stats:
        if line.endswith("stats="):
             fs,ost = line.split(".", 2)[1].split("-")
        elif "_bytes" in line:
            k,count,null,null,min_size,max_size,sum_bytes = line.split()
            post += 'usage,fs={3},ost={4} {0}={1}i {2}\n'.format(k,sum_bytes,ts,fs,ost)
        else:
             k,v,null = line.split(None,2)
             if k == "snapshot_time":
                 ts=int(float(v)*1000000)
             else:
                 post += 'usage,fs={3},ost={4} {0}={1}i {2}\n'.format(k,v,ts,fs,ost)


    post=post.encode('ascii')
    #print post
    p = urllib2.urlopen(url + '/write?db=lustre&precision=u',post)
    print(p.getcode())

#grabbit()


with daemon.DaemonContext():
  while True:
    try:
      grabbit()
    except:
      import sys
      sys.exit("Whoa, that went a bit Pete Tong!")
    time.sleep(10)
