import tweepy
import sqlite3
import time
import datetime
import threading
import logging

class RedLine:
	def __init__(self):
		'''
		Connect to sqlite db and create our API object
		'''
		
		self.CONN = sqlite3.connect('data.db')
		self.CUR = self.CONN.cursor()

		self.CONSUMER_KEY = self.CUR.execute('SELECT Consumer_Key FROM OAuth').fetchone()[0]
		self.CONSUMER_SECRET = self.CUR.execute('SELECT Consumer_Secret FROM OAuth').fetchone()[0]
		self.ACCESS_KEY = self.CUR.execute('SELECT Access_Key FROM OAuth').fetchone()[0]
		self.ACCESS_SECRET = self.CUR.execute('SELECT Access_Secret FROM OAuth').fetchone()[0]

		self.AUTH = tweepy.OAuthHandler(self.CONSUMER_KEY, self.CONSUMER_SECRET)
		self.AUTH.set_access_token(self.ACCESS_KEY, self.ACCESS_SECRET)
		self.API = tweepy.API(self.AUTH)

		self.CTA_ID = self.API.get_user('CTA').id

		self.last_tweet_id = self.CUR.execute('SELECT Last_Tweet FROM Data').fetchone()[0]

	def scan_for_tweets(self):
		'''
		Scan all tweets made since most recent tweet, or the most recent 20 tweets.
		'''

		if self.last_tweet_id == 0:
			logging.info('Getting 20 most recent tweets as starting point.')
			most_recent_twenty = self.API.user_timeline(id=self.CTA_ID)

			# get the absolute most recent status ID
			self.last_tweet_id = most_recent_twenty[0].id
			self.check_if_red_line(most_recent_twenty)
			# push most recent tweet ID to db in case we lose connection
			self.CUR.execute('UPDATE Data SET Last_Tweet = ?', (self.last_tweet_id, )); self.CONN.commit()

		while True:
			cta_tweets_since_last = self.API.user_timeline(id=self.CTA_ID, count=50, since_id=self.last_tweet_id)

			if cta_tweets_since_last:
				self.last_tweet_id = cta_tweets_since_last[0].id
				self.check_if_red_line(cta_tweets_since_last)

				self.CUR.execute("UPDATE Data SET Last_Tweet = ?", (self.last_tweet_id, )); self.CONN.commit()

			logging.debug('Most recent status: %s', self.last_tweet_id)
			logging.debug('Sleeping ... ')
			time.sleep(60)

	def check_if_red_line(self, tweet_list: list):
		'''
		Check list of recent tweets for 'red line' and 'delays'

		Args:
			tweet_list: List of tweets to check.
		'''

		for tweet in tweet_list:
			# we don't want replies to be processed
			if tweet.in_reply_to_status_id is None:
				tweet_text = tweet.text.lower()
				tweet_words = tweet_text.split()
				if 'red' in tweet_words and '[' in tweet_text:
					logging.info('Retweeting status %s.', tweet.id)
					print('Retweeting ' + str(tweet.id) + '\n')
					try:
						self.API.retweet(tweet.id)
						self._increment_incident_tally()
					except tweepy.error.TweepError as e:
						logging.error('ERROR RETWEETING: %s', str(e))

	def _increment_incident_tally(self):
		'''
		Increment the Incidents_Per_Month tally stored in DB.
		'''

		logging.debug('Incrementing Incidents_This_Month ...')
		self.CUR.execute('UPDATE Data SET Incidents_This_Month = Incidents_This_Month + 1')

class CheckDay(RedLine, threading.Thread):
	def __init__(self):
		'''
		Initiliaze RedLine to get our API object and thread
		'''

		RedLine.__init__(self)
		threading.Thread.__init__(self)

	def run(self):
		'''
		Check if it is the 1st of the month every 24 hours.
		'''

		while True:
			logging.debug("Checking if it's the 1st of the month ... ")
			now = datetime.datetime.now()
			if now.day == 1:
				logging.info('Tweeting the monthly tally ...')
				with sqlite3.connect('data.db') as conn:
					cur = conn.cursor()
					incidents_this_month, incidents_last_month = cur.execute('SELECT Incidents_This_Month, Incidents_Last_Month FROM Data').fetchone()
					this_minus_last = incidents_this_month - incidents_last_month
					if this_minus_last > 0:
						self.API.update_status("There were {0} incidents in {1}. That's up {2} from last month.".format(incidents_this_month, now.strftime("%B"), abs(this_minus_last)))
					elif this_minus_last < 0:
						self.API.update_status("There were {0} incidents in {1}. That's down {2} from last month.".format(incidents_this_month, now.strftime("%B"), abs(this_minus_last)))
			time.sleep(84600)

logging.basicConfig(filename='log.log', format='[%(levelname)s] %(asctime)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)

check_day = CheckDay()
check_day.start()

red = RedLine()
red.scan_for_tweets()