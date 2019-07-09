import tweepy
import sqlite3
import time

class RedLine:
	def __init__(self):
		'''
		Connect to sqlite db and get create out API object
		'''

		self.conn = sqlite3.connect('data.db')
		self.cur = self.conn.cursor()

		self.consumer_key = self.cur.execute('SELECT Consumer_Key FROM OAuth;').fetchone()[0]
		self.consumer_secret = self.cur.execute('SELECT Consumer_Secret FROM OAuth;').fetchone()[0]
		self.access_key = self.cur.execute('SELECT Access_Key FROM OAuth;').fetchone()[0]
		self.access_secret = self.cur.execute('SELECT Access_Secret FROM OAuth;').fetchone()[0]

		self.auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
		self.auth.set_access_token(self.access_key, self.access_secret)
		self.api = tweepy.API(self.auth)

		self.cta_id = self.api.get_user('CTA').id

		if self.cur.execute('SELECT Last_Tweet FROM Data;').fetchone() == None:
			# get 20 most recent @CTA tweets as a starting point
			self.cta_tweets = self.api.user_timeline(id=self.cta_id)

			self.last_tweet_id = self.check_if_red_line(self.cta_tweets)
			self.cur.execute('INSERT INTO Data (Last_Tweet) VALUES (?);', (self.last_tweet_id, ))
			self.conn.commit()
			self.scan_for_tweets(self.last_tweet_id)
		
		else:
			# we have a last seen tweet saved in db; use this to scan
			self.scan_for_tweets(self.cur.execute('SELECT Last_Tweet FROM Data;').fetchone()[0])

	def scan_for_tweets(self, last_tweet_id):
		'''
		Scan all tweets made since last most recent tweet.

		:param int last_tweet_id: The largest (most recent) tweet ID from @CTA.
		'''

		while(True):
			print('Sleeping ... \n')
			time.sleep(60)
			cta_tweets_since_last = self.api.user_timeline(id=self.cta_id, since_id=last_tweet_id)
			
			if cta_tweets_since_last:
				self.check_if_red_line(cta_tweets_since_last)

	def check_if_red_line(self, tweet_list):
		'''
		Check list of recent tweets for 'red line' and 'delays'

		:param list tweet_list: List of the tweets the check.
		:return: The id of the most recent tweet from the list.
		:rtype: int
		'''

		for tweet in tweet_list:
			tweet_text = tweet.text.lower()
			if 'red line' in tweet_text and 'delays' in tweet_text:
				# retweet the Red Line alert we found
				print('Retweeting ' + str(tweet.id) + '\n')
				# self.api.retweet(tweet.id)

		# save most recent tweet we found to db
		last_tweet_id = tweet_list[0].id
		self.cur.execute("UPDATE Data SET Last_Tweet = ?;", (last_tweet_id, ))
		self.conn.commit()

		return last_tweet_id

red = RedLine()