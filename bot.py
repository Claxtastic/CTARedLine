import tweepy
import sqlite3

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

def startup():
	'''
	If bot just went online, do an initial scan of @CTA's 20 most recent tweets.
	'''

	# get 20 most recent @CTA tweets
	cta_tweets = API.user_timeline(CTA_ID)

	for tweet in cta_tweets:
		tweet_text = tweet.text.lower()
		if 'red line' in tweet_text and 'delays' in tweet_text:
			# retweet the Red Line alert we found
			print('Retweeting ' + str(tweet.id) + '\n')
		
	# save the tweet.id of the most recent tweet we discovered
	CUR.execute("INSERT INTO Data (Last_Tweet) VALUES (?)", (cta_tweets[0].id, ))
	CONN.commit()

	main_loop()

def main_loop():
	cta_tweets_since_last = API.user_timeline

startup()