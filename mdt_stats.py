#!/usr/bin/python2.7

# Script to spit out lustre stats towards an influxdb server
# Andrew Elwell <Andrew.Elwell@pawsey.org.au>, Sept 2017. Available under GPL2+ 
# Hints from http://wiki.lustre.org/Lustre_Monitoring_and_Statistics_Guide 

import urllib2
import time
import os
import fnmatch
import subprocess

import daemon

# which nutter enabled auth on influx
username = 'FIXME'
password = 'FIXME'
url = "https://influx.example.org:8086"
pw = urllib2.HTTPPasswordMgr()
pw.add_password("InfluxDB", url, username, password)
handler = urllib2.HTTPBasicAuthHandler(pw)
opener = urllib2.build_opener(handler)
urllib2.install_opener(opener)



# While I should really use 'lctl get_param', grabbing the source directly saves an extra subprocess

def getrole():
    # are we running on an MDT?
    mdslist = os.listdir('/proc/fs/lustre/mdt/')
    if len(mdslist) == 1:
        mds = mdslist[0]
        (fs,mdt) = mds.split('-',2)
    return (mds,fs,mdt)

def grabbit(info):
    (mds,fs,mdt) = info
    post = ""
    with open(('/proc/fs/lustre/mdt/%s/md_stats' % mds), 'r') as f:
        for line in f:
            k,v,null = line.split(None,2)
            if k == "snapshot_time":
                ts=int(float(v)*1000000)
            else:
               post += 'metadata,fs={3},mdt={4},mds={5} {0}={1}i {2}\n'.format(k,v,ts,fs,mdt,mds)
    with open(('/proc/fs/lustre/mdd/%s/changelog_users' % mds), 'r') as f:
       tmp = f.read().split()
       # we can cheat here as they have the same format - 3rd item in list is current changelog count, and then
       # from the 6th item on we get changelog id / position to pull into a dict
       head = int(tmp[2])
       clog = dict(zip(tmp[5:][0::2], tmp[5:][1::2]))
       post += 'changelog,fs={2},mdt={3},mds={4} head={0}i {1}\n'.format(head,ts,fs,mdt,mds)
       for cl,count in clog.items():
           post += 'changelog,fs={3},mdt={4},mds={5} {0}={1}i {2}\n'.format(cl,count,ts,fs,mdt,mds)

    ts = int(time.time()*1000000)
    mdtstats = subprocess.check_output(["lctl","get_param", "osd-*.*MDT*.files*"]).splitlines()
    for stat in mdtstats:
        keys,val = stat.split("=")
        _, mds, metric = keys.split(".", 2)
        fs,mdt = mds.split("-")

        post += 'usage,fs={0},mdt={1},mds={2} {3}={4}i {5}\n'.format(fs,mdt,mds,metric,val,ts)
 
    post=post.encode('ascii')
    print post
    p = urllib2.urlopen(url + '/write?db=lustre&precision=u',post)
    print(p.getcode())

#foo = getrole()
#grabbit(foo)


with daemon.DaemonContext():
  foo = getrole()
  while True:
    try:
      grabbit(foo)
    except:
      # import sys
      # sys.exit("Whoa, that went a bit Pete Tong!")
      time.sleep(30)
    time.sleep(10)
