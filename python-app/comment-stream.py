#!/usr/bin/python
import praw
import re
import datetime
import sys
import boto3
import json
import time
import logging
import pandas as pd
from textblob import TextBlob
from textblob import Blobber
from better_profanity import profanity

def remove_emoji(comment):
    emoji_pattern = re.compile("["
       u"\U0001F600-\U0001F64F"  # emoticons
       u"\U0001F300-\U0001F5FF"  # symbols & pictographs
       u"\U0001F680-\U0001F6FF"  # transport & map symbols
       u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
       u"\U00002702-\U00002f7B0"
       u"\U000024C2-\U0001F251"
       "]+", flags=re.UNICODE)

    cleaned_comment =  emoji_pattern.sub(r'', comment)

    return cleaned_comment

def get_comment_sentiment(comment):
    pattern_analysis = TextBlob(comment)
    return pattern_analysis.sentiment


def process_or_store(comment):
    try:
        response = firehose_client.put_record(
            DeliveryStreamName='<insert-delivery-stream-name>',
            Record={
                'Data': (json.dumps(comment, ensure_ascii=False) + '\n').encode('utf8')
                    }
            )
        logging.info(response)
    except Exception:
        logging.exception("Problem pushing to firehose")


firehose_client = boto3.client('firehose', region_name="us-east-1")
LOG_FILENAME = '/tmp/reddit-stream.log'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

if len(sys.argv) >= 2:
    try:
        r = praw.Reddit('bot1')
        num_comments_collected = 0

        # build stream. add first subreddit to start.
        subreddits = sys.argv[1]
        for sr in sys.argv[2:]:
            subreddits = subreddits + "+" + sr

        comment_stream = r.subreddit(subreddits)

        for comment in comment_stream.stream.comments():
            if profanity.contains_profanity(str(comment.body)):
                is_censored = 1
            else:
                is_censored = 0

            cleaned_comment = profanity.censor((remove_emoji(str(comment.body))))
            comment_date = str(datetime.datetime.utcfromtimestamp(comment.created_utc).strftime('%Y/%m/%d %H:%M:%S'))
            sentiment = get_comment_sentiment(cleaned_comment)
            pattern_polarity = round(sentiment.polarity,4)


            commentjson = {
            			  '@timestamp' : comment_date,
                          'comment_id': comment.id,
                           'subreddit': str(comment.subreddit),
                           'comment_body': cleaned_comment,
                           'comment_distinguished': comment.distinguished,
                           'comment_is_submitter': comment.is_submitter,
                           'comment_tb_sentiment': pattern_polarity,
                           'comment_is_censored': is_censored,
		           'author_name': str(comment.author.name)
                           }
            print("==================================")
            num_comments_collected = num_comments_collected + 1
            print(num_comments_collected)
            print(commentjson)
            process_or_store(commentjson)
    except Exception as e:
        print(e)
else:
    print("please enter subreddit.")
