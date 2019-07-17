import tweepy
import sqlite3
import time
import datetime
import threading

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
		self.scan_for_tweets()

	def scan_for_tweets(self):
		'''
		Scan all tweets made since most recent tweet, or the most recent 20 tweets.
		'''

		if self.last_tweet_id == 0:
			# get 20 most recent @CTA tweets as a starting point
			print('Getting starting point')
			most_recent_twenty = self.API.user_timeline(id=self.CTA_ID)

			# update the most recent tweet ID instance variable
			self.last_tweet_id = most_recent_twenty[0].id

			self.check_if_red_line(most_recent_twenty)
			# push most recent tweet ID to db in case we lose connection
			self.CUR.execute('UPDATE Data SET Last_Tweet = ?', (self.last_tweet_id, )); self.CONN.commit()

		while True:
			cta_tweets_since_last = self.API.user_timeline(id=self.CTA_ID, count=50, since_id=self.last_tweet_id)

			if cta_tweets_since_last:
				self.last_tweet_id = cta_tweets_since_last[0].id
				self.check_if_red_line(cta_tweets_since_last)

				# save most recent tweet we found to db
				self.CUR.execute("UPDATE Data SET Last_Tweet = ?", (self.last_tweet_id, )); self.CONN.commit()

			print(self.last_tweet_id)
			print('Sleeping ... \n')
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
				print(tweet_text)
				input()
				# split the tweet on white space to match whole words
				tweet_words = tweet_text.split()
				if 'red' in tweet_words and '[' in tweet_text:
					# retweet the Red Line alert we found
					print('Retweeting ' + str(tweet.id) + '\n')
					try:
						self.API.retweet(tweet.id)
						self._increment_incident_tally()
					except tweepy.error.TweepError as e:
						print('Error retweeting: ' + str(e))

	def _increment_incident_tally(self):
		'''
		Increment the Incidents_Per_Month tally stored in DB.
		'''

		self.CUR.execute('UPDATE Data SET Incidents_Per_Month = Incidents_Per_Month + 1')

def check_day():
	'''
	Check if it is the 1st of the month every 24 hours.
	'''

	while True:
		now = datetime.datetime.now()
		if now.day == 1:
			# tweet the tally tweet
			print('Tweeting tally ... ')
			'''
			this_minus_last = [Incidents_This_Month] - [Incidents_Last_Month]
			if this_minus_last > 0:
				api.tweet('There were [Incidents_This_Month]. That's up [this_minus_last] from last month.)
			else if this_minus_last < 0:
				api.tweet('There were [Incidents_This_Month]. That's down [abs(this_minus_last)] from last month.)
			'''
		time.sleep(84600)

day_check_thread = threading.Thread(target=check_day)
day_check_thread.start()

red = RedLine()