from __future__ import print_function
from twitter import Twitter, OAuth, TwitterHTTPError
import os
import sys
import time
import random

from TwitterFollowBot import TwitterBot


class PyBot:

    def __init__(self):
        self.bot = TwitterBot()
        self.bot.sync_follows()

    def work(self, phrase):
        result = self.bot.search_tweets(phrase, 100, "recent")
        for tweet in result["statuses"]:
            try:
                # don't retweet your own tweets
                if tweet["user"]["screen_name"] == self.bot.BOT_CONFIG["TWITTER_HANDLE"]:
                    continue

                # self.bot.wait_on_action()
                result = self.bot.TWITTER_CONNECTION.statuses.retweet(id=tweet["id"])
                print("Retweeted: %s" % (result["text"].encode("utf-8")))
                result = self.bot.TWITTER_CONNECTION.favorites.create(_id=tweet["id"])
                print("Favorited: %s" % (result["text"].encode("utf-8")), file=sys.stdout)


            # when you have already retweeted a tweet, this error is thrown
            except TwitterHTTPError as api_error:
                # quit on rate limit errors
                if "rate limit" in str(api_error).lower():
                    print("You have been rate limited. "
                          "Wait a while before running the bot again.")
                    return

                print("Error: %s" % (str(api_error)))

    def stop_work(self):
        raise SystemExit()
