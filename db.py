import sqlite3

conn = sqlite3.connect('data.db')
cur = conn.cursor()

try:
	cur.execute('CREATE TABLE Data (Last_Tweet NUMBER, Incidents_Per_Month NUMBER)')
	cur.execute('CREATE TABLE OAuth (Consumer_Key TEXT, Consumer_Secret TEXT, Access_Key TEXT, Access_Secret TEXT)')
except sqlite3.OperationalError:
	pass

print('Enter Consumer Key: \n')
consumer_key = input()

print('Enter Consumer Secret: \n')
consumer_secret = input()

print('Enter Access Key: \n')
access_key = input()

print('Enter Access Secret: \n')
access_secret = input()

cur.execute('INSERT INTO OAuth VALUES (?, ?, ?, ?)', (consumer_key, consumer_secret, access_key, access_secret))
conn.commit()

cur.close()
conn.close()