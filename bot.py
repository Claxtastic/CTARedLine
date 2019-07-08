import tweepy
import sqlite3
import time

CONN = sqlite3.connect('data.db')
CUR = CONN.cursor()

CONSUMER_KEY = CUR.execute('SELECT Consumer_Key FROM OAuth;').fetchone()[0]
CONSUMER_SECRET = CUR.execute('SELECT Consumer_Secret FROM OAuth;').fetchone()[0]
ACCESS_KEY = CUR.execute('SELECT Access_Key FROM OAuth;').fetchone()[0]
ACCESS_SECRET = CUR.execute('SELECT Access_Secret FROM OAuth;').fetchone()[0]

AUTH = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
AUTH.set_access_token(ACCESS_KEY, ACCESS_SECRET)
API = tweepy.API(AUTH)

CTA_ID = API.get_user('CTA').id

def init():
	'''
	If bot just went online, do an initial scan of @CTA's 20 most recent tweets.
	'''

	# get 20 most recent @CTA tweets
	cta_tweets = API.user_timeline(id=CTA_ID)

	last_tweet_id = check_if_red_line(cta_tweets)
	main_loop(last_tweet_id)

def main_loop(last_tweet_id):
	'''
	Main loop that uses the most recent discovered tweet as epoch for future scans.
	'''

	while(True):
		print('Sleeping ... \n')
		time.sleep(60)
		cta_tweets_since_last = API.user_timeline(id=CTA_ID, since_id=last_tweet_id)
		
		if cta_tweets_since_last:
			check_if_red_line(cta_tweets_since_last)

def check_if_red_line(tweet_list):
	for tweet in tweet_list:
		tweet_text = tweet.text.lower()
		if 'red line' in tweet_text and 'delays' in tweet_text:
			# retweet the Red Line alert we found
			print('Retweeting ' + str(tweet.id) + '\n')

	# save most recent tweet we found to db
	last_tweet_id = tweet_list[0].id
	CUR.execute("INSERT INTO Data (Last_Tweet) VALUES (?)", (last_tweet_id, ))
	CONN.commit()

	return last_tweet_id

init()