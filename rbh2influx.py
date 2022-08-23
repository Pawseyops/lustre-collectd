#!/usr/bin/python3

# rbh-report to influx publisher
# Andrew Elwell <Andrew.Elwell@pawsey.org.au>, July 2020
import time
import subprocess
import csv
import requests


askapgroups = ['askap', 'askaprt', 'casda']
mwagroups = ['mwaops', 'mwasci', 'mwavcs', 'mwaeor']
mount_name = {'askapfs1': 'askapbuffer', 'snx11038': 'scratch',
              'astrofs': 'astro', 'pgfs': 'group',
              'askapfs2': 'askapingest', 'testfs': 'testfs'
             }

def parsemounts():
    """See which lustre filesystems are currently mounted"""
    filesystems = []
    with open('/proc/mounts', 'r') as mounts:
        for line in mounts:
            device, mount, fstype, crap = line.split(maxsplit=3)
            if fstype == 'lustre':
                fsname = device.split(':')[-1].lstrip('/')
                #print(mount, device, fsname)
                filesystems.append(fsname)
    return filesystems

for fs in parsemounts():
    data = ''
    askapout = ''
    mwaout = ''
    rbh=subprocess.check_output(['/usr/sbin/rbh-report',
                 '-f', '/etc/robinhood.d/'+ fs +'.conf',
                 '--group-info' , '--csv', '--no-header', '-S']
                 ).decode('utf8').splitlines()
    ts = time.time()
    cols = ['group','user','type','count','volume','spc_used','avg_size']
    reader = csv.DictReader(rbh,cols,skipinitialspace=True)
    for row in reader:
        if int(row['count']) > 0:
            data += "robinhood,fs={},mount={},group={},user={},type={} count={},volume={},spc_used={},avg_size={} {}\n".format(
                     fs, mount_name[fs], row['group'], row['user'],
                     row['type'], row['count'], row['volume'], row['spc_used'],
                     row['avg_size'],int(ts)
                     )
            if row['group'] in askapgroups:
                askapout += "robinhood,fs={},mount={},group={},user={},type={} count={},volume={},spc_used={},avg_size={}\n".format(
                             fs, mount_name[fs], row['group'], row['user'],
                             row['type'], row['count'], row['volume'],
                             row['spc_used'], row['avg_size']
                             )
            if row['group'] in mwagroups:
                mwaout += "robinhood,fs={},mount={},group={},user={},type={} count={},volume={},spc_used={},avg_size={}\n".format(
                           fs, mount_name[fs], row['group'], row['user'],
                           row['type'], row['count'], row['volume'],
                           row['spc_used'], row['avg_size']
                           )

    rbh=subprocess.check_output(['/usr/sbin/rbh-report',
                 '-f', '/etc/robinhood.d/'+ fs +'.conf',
                 '--group-info' , '--csv', '--no-header']
                 ).decode('utf8').splitlines()
    ts = time.time()
    cols = ['group','type','count','volume','spc_used','avg_size']
    reader = csv.DictReader(rbh,cols,skipinitialspace=True)
    for row in reader:
        if int(row['count']) > 0:
            data += "rbh-summary,fs={},mount={},group={},type={} count={},volume={},spc_used={},avg_size={} {}\n".format(
                     fs, mount_name[fs], row['group'], row['type'],
                     row['count'], row['volume'], row['spc_used'],
                     row['avg_size'], int(ts)
                     )
            if row['group'] in askapgroups:
                askapout += "rbh-summary,fs={},mount={},group={},type={} count={},volume={},spc_used={},avg_size={}\n".format(
                             fs, mount_name[fs], row['group'], row['type'],
                             row['count'], row['volume'],
                             row['spc_used'], row['avg_size']
                             )
            if row['group'] in mwagroups:
                mwaout += "rbh-summary,fs={},mount={},group={},type={} count={},volume={},spc_used={},avg_size={}\n".format(
                           fs, mount_name[fs], row['group'], row['type'],
                           row['count'], row['volume'],
                           row['spc_used'], row['avg_size']
                           )
    #print(data)
    requests.post('https://influx2.pawsey.org.au:8086/write?db=lustre&precision=s', data, auth=('USERNAME','PASSWORD'))
    if askapout:
        #print (askapout)
        try:
            r = requests.post('REDACTED_ASKAP_SERVER/write?db=pawsey_lustre&precision=s',
                  data=askapout, timeout=1.5,
                  auth=('REDACTED_ASKAP_USER', 'REDACTED_ASKAP_KEY')
                  )
            #print(r.status_code)
        except requests.Timeout:
            #print('DEBUG: Request timed out to ASKAP')
            pass
        except requests.ConnectionError as err:
            #print('DEBUG: Connection error to ASKAP:',err)
            pass
    if mwaout:
        try:
            #print (mwaout)
            r = requests.post('REDACTED_MWA_SERVERwrite?db=lustre&precision=s', data=mwaout,timeout=1.5)
            #print('DEBUG: return code = {}'.format(r.status_code))
            #print('DEBUG: headers = {}'.format(r.headers))
            #print(r.reason)
        except requests.Timeout:
            #print('DEBUG: Request timed out to MWA')
            pass
        except requests.ConnectionError as err:
            #print('DEBUG: Connection error to MWA: ',err)
            pass
