#! /usr/bin/env python

import feedparser
import re
import pickle
import sys, os
import sqlite3
import httplib2
import random

import sendEmail

from time import mktime, sleep
from datetime import datetime

class Feed:
	feedStaleTime = 60 * 60 * 6 # 60 sec * 60 min * 6 = six hours
	
	def __init__(self, name, url, owner, email):
		self.feedName = name
		self.feedURL = url
		self.feedOwner = owner
		self.feedOwnerEmail = email
		self.feedData = []
		self.rawFeedData = None
		self.feedDBConnection = None
		self.feedDBCursor = None
		self.dbTableName = "{0}_{1}".format(self.feedName, self.feedOwner)
		self.feedCacheFile = "{0}_{1}.dat".format(self.feedName, self.feedOwner)
		self.readFromCache()
		self.dbConnect()
		if not self.dbTableExists():
			print("Creating database table")
			self.createTable()

	
	def readFromCache(self):
		print("Attempting to read previously stored feed data")
		try:
			fh = open(self.feedCacheFile, 'rb')
			self.rawFeedData = pickle.load(fh)
			print("Reading stored feed data.")
			fh.close()
		except (IOError, OSError, EOFError):
			print("Cached data unreadable. Retrieving fresh feed data...")
			self.rawFeedData = feedparser.parse(self.feedURL)
		self.parseRawFeedData()
		self.saveFeed()

	def displayTitles(self):
		for entry in self.rawFeedData['items']:
			print(entry['title'])

	def saveFeed(self):
		# Context manager
		with open(self.feedCacheFile, 'wb') as outFile:
			print("Storing feed data to {0}".format(self.feedCacheFile))
			pickle.dump(self.rawFeedData, outFile)

	# returns a datetime timestamp, of last modification of datafile	
	def getFeedTime(self):
		return datetime.fromtimestamp(os.path.getmtime(self.feedCacheFile))

	def isFeedFresh(self):
		now = datetime.now()
		t_delta = now - self.getFeedTime()
		if t_delta.total_seconds() > self.feedStaleTime:
			return False
		return True
		
	def refreshFeed(self, forceRefresh = False):
		if not self.isFeedFresh() or forceRefresh is True:
			self.rawFeedData = feedparser.parse(self.feedURL)
			self.saveFeed(self.rawFeedData)

	def dbConnect(self):
		self.feedDBConnection = sqlite3.connect("mydatabase.db")
		self.feedDBCursor = self.feedDBConnection.cursor()

	def dbTableExists(self):
		selectStmt = "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{0}';".format(self.dbTableName)
		self.feedDBCursor.execute(selectStmt)
		row = self.feedDBCursor.fetchone()[0]
		if not row:
			return False
		return True

	def createTable(self):
		tableStmt = "CREATE TABLE {0} (title text, link text, summary text, published_time integer, updated_time integer)".format(self.dbTableName)
		self.feedDBCursor.execute(tableStmt)

	def parseRawFeedData(self):
		self.feedData = []
		entryDict = {}
		for entry in self.rawFeedData["items"]:
			entryDict = {"title": entry['title'],
									"link": entry['link'],
									"summary": entry['summary'],
									"published_time": self.timeStructToEpoch(entry['published_parsed']),
									"updated_time": self.timeStructToEpoch(entry['updated_parsed']),
									}
			self.feedData.append(entryDict)

	def timeStructToEpoch(self, timeStruct):
		return mktime(timeStruct)

	def fillTable(self):
#		insertStmt = """INSERT INTO {0} VALUES (?, ?, ?, ?, ?)""".format(self.dbTableName)
#		self.feedDBCursor.execute(insertStmt, ("test", "testlink", "a summary", 11235, 1255656))
		for item in self.feedData:
			insertStmt = """INSERT INTO {0} (title, link, summary, published_time, updated_time)
									VALUES (:title, :link, :summary, :published_time, :updated_time)""".format(self.dbTableName)
#			print(insertStmt, item)
			self.feedDBCursor.execute(insertStmt, item)
		self.feedDBConnection.commit()

	def webGet(self, link):
		h = httplib2.Http(".cache")
		resp, content = h.request(link, "GET")
		return content

	def getAllImages(self, link):
		print("Getting image URLS from listing {0}".format(link))
		listingHTML = self.webGet(link)
		m = re.search(r"imgList = \[(.*)\].*\n", listingHTML)
		images = []
		if m:
			images = m.groups()[0].translate(None, '"').split(',')
		for imageURL in images:
			sleep(2)
			self.getPic(imageURL)
		return images

	def getPic(self, imageURL):
		print("Getting image from {0}".format(imageURL))
		fname = os.path.basename(imageURL)
		
		if not os.path.exists(fname):
			imageData = self.webGet(imageURL)
			fname = os.path.basename(imageURL)
			with open(fname, 'wb') as outFile:
				outFile.write(imageData)

	def createEmailBody(self, listing):
		msgBody  = "Hey, look {0}!\r\n\r\nI found some cool stuff (about {1}!) for you on Craiglist!\r\n".format(self.feedOwner, self.feedName)
		
		clTitle = listing['title'][:50]
		if listing['title'] != clTitle:
			clTitle = clTitle[:47] + "..."
		clLink = listing['link']
		
		msgBody += "{0} : {1}\r\n".format(clTitle, clLink)
		return msgBody

#feeds = [
	#("http://sandiego.craigslist.org/search/?areaID=8&subAreaID=&query=pellet+stove&catAbb=sss&format=rss",
		#"julinjoe@gmail.com",
		#"",
	#),
	#("http://sandiego.craigslist.org/search/apa?query=north+park&srchType=A&minAsk=&maxAsk=1400&bedrooms=2&format=rss",
		#"clare.estelle@gmail.com;billysanders@gmail.com",
		#"",
	#),
#]

# If file called as a script from the command line, run this
if __name__ == "__main__":
	testfeed = ("Chickens", "http://sandiego.craigslist.org/search/gra?hasPic=1&query=chickens&srchType=A&format=rss", "Clare", "clare.estelle@gmail.com")

	random.seed()

	# unpack the tuple for arguments
	myfeed = Feed(*testfeed)

	myfeed.fillTable()

	images = []
	if 'hasPic=1' in myfeed.feedURL:
		random_listing = random.choice(myfeed.feedData)
		images = myfeed.getAllImages(random_listing['link'])

	images = [os.path.basename(img) for img in images]
	
	#get credentials here
	
	sendEmail.smtp(username, password)
	sendEmail.sendEmail([myfeed.feedOwnerEmail], "Cool Craiglist Stuff", myfeed.createEmailBody(random_listing), images)
