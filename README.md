Lustre stats to influxdb publisher

The 2 scripts here (mdt_stats.py and ost_stats.py) are designed to be run on the MDS and OSS servers respectively.
they parse the changelog counter and metadata and per-ost stats files and publish to an influxdb server where 
the results can be plotted say with Grafana

Please contact Andrew Elwell <andrew.elwell@pawsey.org.au> or the Pawsey Helpdesk (help@pawsey.org.au) with any questions
