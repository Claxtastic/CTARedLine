import os
import tweepy
import sqlite3
import time
import datetime
import threading
import logging
import logging.handlers as handlers

class RedLine:
	def __init__(self):
		'''
		Connect to sqlite db and create our API object
		'''
		
		self.CONN = sqlite3.connect('data.db')
		self.CUR = self.CONN.cursor()

		self.check_and_set_environment()

		self.AUTH = tweepy.OAuthHandler(self.CONSUMER_KEY, self.CONSUMER_SECRET)
		self.AUTH.set_access_token(self.ACCESS_KEY, self.ACCESS_SECRET)
		self.API = tweepy.API(self.AUTH)

		self.CTA_ID = self.API.get_user('CTA').id

		self.last_tweet_id = self.CUR.execute('SELECT Last_Tweet FROM Data').fetchone()[0]

	def check_and_set_environment():
		if os.environ.get('CONSUMER_KEY') is not None:
			try:
				cur.execute('CREATE TABLE Data (Last_Tweet NUMBER, Incidents_This_Month NUMBER, Incidents_Last_Month NUMBER)')
				cur.execute('CREATE TABLE OAuth (Consumer_Key TEXT, Consumer_Secret TEXT, Access_Key TEXT, Access_Secret TEXT)')
			except sqlite3.OperationalError:
				pass
			# on heroku
			self.CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
			self.CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')
			self.ACCESS_KEY = os.environ.get('ACCESS_KEY')
			self.ACCESS_SECRET = os.environ.get('ACCESS_SECRET')
		else:
			self.CONSUMER_KEY = self.CUR.execute('SELECT Consumer_Key FROM OAuth').fetchone()[0]
			self.CONSUMER_SECRET = self.CUR.execute('SELECT Consumer_Secret FROM OAuth').fetchone()[0]
			self.ACCESS_KEY = self.CUR.execute('SELECT Access_Key FROM OAuth').fetchone()[0]
			self.ACCESS_SECRET = self.CUR.execute('SELECT Access_Secret FROM OAuth').fetchone()[0]

	def scan_for_tweets(self):
		'''
		Scan all tweets made since most recent tweet, or the most recent 20 tweets.
		'''

		logging.info('Starting ...')
		print('Starting ... \n')

		if self.last_tweet_id == 0:
			logging.info('Getting 10 most recent tweets as starting point.')
			most_recent_five = self.API.user_timeline(id=self.CTA_ID, count=10)
			# reverse the list so the most recent tweet is last
			most_recent_five.reverse()

			# get the absolute most recent status ID
			self.last_tweet_id = most_recent_five[-1].id
			self.check_if_red_line(most_recent_five)
			# push most recent tweet ID to db in case we lose connection
			self.CUR.execute('UPDATE Data SET Last_Tweet = ?', (self.last_tweet_id, )); self.CONN.commit()

		while True:
			cta_tweets_since_last = self.API.user_timeline(id=self.CTA_ID, count=10, since_id=self.last_tweet_id)

			if cta_tweets_since_last:
				self.last_tweet_id = cta_tweets_since_last[-1].id
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
					print('Retweeting ' + 'https://twitter.com/cta/status/' + str(tweet.id) + '\n')
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
		Initialize RedLine to get our API object and thread
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
					delta = incidents_this_month - incidents_last_month
					if delta > 0:
						self.API.update_status("There were {0} incidents in {1}. That's up {2} from last month.".format(incidents_this_month, now.strftime("%B"), abs(delta)))
					elif delta < 0:
						self.API.update_status("There were {0} incidents in {1}. That's down {2} from last month.".format(incidents_this_month, now.strftime("%B"), abs(delta)))
					
					# set this month's incident total to be last month's
					cur.execute('INSERT INTO Data Incidents_Last_Month = {0}'.format(incidents_this_month))
					# reset counter for this month
					cur.execute('UPDATE Data SET Incidents_This_Month = 0')
			time.sleep(84600)

###### Setup Logger ######
log_name = 'log/log.log'
logger = logging.getLogger('')
logger.setLevel(logging.INFO)

formatter = logging.Formatter('[%(levelname)s] %(asctime)s: %(message)s')

log_handler = handlers.TimedRotatingFileHandler(log_name, when="midnight", interval=1)
log_handler.setLevel(logging.INFO)
log_handler.suffix = "%m%d%Y"
log_handler.setFormatter(formatter)

logger.addHandler(log_handler)
##########################

######### Start ##########
# thread to check the day
check_day = CheckDay()
check_day.start()

red = RedLine()
# start loop
red.scan_for_tweets()
##########################
