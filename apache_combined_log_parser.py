#!/usr/bin/env python
# -*- coding: utf-8-*-

"""
This script parses a directory of Apache log files and prints:
- The percentage of off-site requests
- The top 10 URLs
- The customer usage summary
"""

import shlex, os
from urlparse import urlparse

# Indexes of fields record
REQUEST_INDEX = 5
HTTP_CODE_INDEX = 6
BYTES_INDEX = 7
REFERRER_INDEX = 8

# A request is considered succesful if it begins with the following value 
HTTP_SUCCESS_CODE = "2"

# Maximum number of popular urls to save
POPULAR_URLS_LIMIT = 10

# Gigabyte definition
GIGABYTE = 1073741824.0

# An URL is considered onsite when his host part contains this string
ONSITE = "example.com"


class LogResults:
	"""
	Represents the results for a single Apache log file.
	"""
	def __init__(self, requests=(), customer_usage={}, popular_urls={}):
		# (total_offsite_requests, total_records, percentage_offsite_requests)
		self.requests = requests
		if len(requests) == 0:
			self.requests = (0,0,0)
		
		# {'cust_name': usage}
		self.customer_usage = customer_usage
		
		# {'popular_url': frequency}
		self.popular_urls = popular_urls
		

	def __str__(self):
		return "\nRequests: %s, \nCustomer usage: %s, Popular URLS: \n%s" % \
						(self.requests, self.customer_usage, self.popular_urls)


def reduce_records(rec1, rec2):
	""" Sum the two given records and returns a new one. """

	record = LogResults()

	# Sum customer usage
	for k in set(rec1.customer_usage.keys() + rec2.customer_usage.keys()):
		record.customer_usage[k] = rec1.customer_usage.get(k, 0) + rec2.customer_usage.get(k, 0)

	# Sum requests
	record.requests = rec1.requests[0] + rec2.requests[0], rec1.requests[1] + rec2.requests[1]	

	# Sum popular urls
	for k in set(rec1.popular_urls.keys() + rec2.popular_urls.keys()):
		record.popular_urls[k] = rec1.popular_urls.get(k, 0) + rec2.popular_urls.get(k, 0)

	return record
	
		
def parse_log_file(log_file):
	"""
	Parse a log file and extracts all the information required
	"""
	
	total_records = 0
	total_offsite_requests = 0
	customers_usage = {}
	popular_urls = {}

	with open(log_file) as f:
		for record_line in f: 
			# Extract the tokens we need, shlex.split works almost perfectly out of the box
			# so no need for a regular expression.
			record_tokens = shlex.split(record_line)
			request, http_code, bytes, referrer = record_tokens[REQUEST_INDEX].split()[1], \
							record_tokens[HTTP_CODE_INDEX], \
							int(record_tokens[BYTES_INDEX]), \
							record_tokens[REFERRER_INDEX]
			username = request.split("/")[1]
			
			# Calculate bytes usage by user
			customers_usage[username] = customers_usage.get(username, 0) + bytes
			
			# Populate popular urls frequency map
			if http_code.startswith(HTTP_SUCCESS_CODE):
				popular_urls[request] = popular_urls.get(request, 0) + 1
			
			# Check if request is offsite
			if ONSITE not in urlparse(referrer).netloc:
				total_offsite_requests += 1 
		
			total_records += 1
	
	return LogResults((total_offsite_requests, total_records), customers_usage, popular_urls)
	


def log_files_in_directory(dir_name):
	"""
	Returns the paths of all the log files in a directory
	"""
	return [os.path.join(dir_name, file_name) for file_name in os.listdir(dir_name) if not file_name.startswith(".")]


def help():
	print "Invoke the script with the path of a directory."
	print "Ex. apache_log_parser.py /path/to/dir"
	

if __name__ == "__main__":
	import sys
	
	if len(sys.argv) < 2:
		help()
		exit("Bye")
	
	directory_name = sys.argv[1]
	log_files = log_files_in_directory(directory_name)

	aggregate_results = LogResults()
	for log_file in log_files:
		rec_result = parse_log_file(log_file)
		aggregate_results = reduce_records(aggregate_results, rec_result)

	percentage_offsite_requests = (0.0 + aggregate_results.requests[0]) / aggregate_results.requests[1] * 100

	print "\nOff-site requests: %s of %s (%.2f %%)" % (aggregate_results.requests[0], \
													aggregate_results.requests[1], \
													percentage_offsite_requests)
													
	print "\nTop %s URLs:" % POPULAR_URLS_LIMIT
	popular_urls = sorted(aggregate_results.popular_urls.items(), key=lambda x:x[1], reverse=True)[:POPULAR_URLS_LIMIT]
	for popular_url in popular_urls:
		print "\t %s - %s" % (popular_url[1], popular_url[0])
		
	print "\nCustomer usage summary:"
	for customer_name, customer_usage in aggregate_results.customer_usage.iteritems():
		print "\t %.2f GB - %s" % (customer_usage/GIGABYTE, customer_name) 
	
