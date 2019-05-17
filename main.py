from bs4 import BeautifulSoup
import requests
from requests.auth import HTTPBasicAuth
import json
import re
import sys
import pytumblr
import os


# Sina weibo API Key, get yours at https://open.weibo.com
API_KEY = "<SINA_WEIBO_API_KEY>"
# Sina weibo API URL
URL = "https://api.weibo.com/2/statuses/show.json"
# Used by BS4 to parse a weibo post
BSURL = "https://m.weibo.cn/detail/"

# Tumblr client key, get yours at https://api.tumblr.com/console/calls/user/info
TUMBLR_CLIENT = pytumblr.TumblrRestClient(
    "<consumer_key>", "<consumer_secret>", "<oauth_token>", "<oauth_secret>"
)

# Streamable API to upload video
STREAMABLE_URL = "https://api.streamable.com/upload"
# Stremable credentials, get yours at https://streamable.com/documentation
STREAMABLE_AUTH = HTTPBasicAuth("<EMAIL>", "<PASSWORD>")

# Presistent request session
session = requests.Session()


def parseContent(URL):
    """
    Return a dict:
    result = { "originalText" : "Original Weibo Text",
            "videoURL" : "Video URL, could be none",
            "retweetText" : "Retweet Text, could be none",
            "retweetUser" : "Retweet User name,
            "haveVideo" : Boolean
    }
    """
    r = session.get(URL)
    soup = BeautifulSoup(r.text, "lxml")

    script = soup.find(lambda tag: tag.name == "script" and "render_data" in tag.text)
    codeblock = script.prettify()

    my_regex = r"render_data = \[((.*\n*)*?\})"
    result = re.search(my_regex, codeblock, re.MULTILINE)
    obj = json.loads(result.group(1))

    try:
        weibo = obj["status"]
    except KeyError as e:
        print(str(e))
        sys.exit(1)

    originalText = None
    videoURL = None
    retweetUser = None
    retweetText = None
    haveVideo = False

    isLongText = weibo.get("isLongText", False)
    if isLongText:
        try:
            originalText = weibo["longText"]["longTextContent"]
        except KeyError as e:
            print(str(e))
            print(
                "Was expecting longtext but key does not exist,using original text as default"
            )
            originalText = weibo["text"]
    else:
        originalText = weibo["text"]

    if "retweeted_status" in weibo:
        print("this is a retweet")
        retweet = weibo["retweeted_status"]
        retweetUser = retweet["user"]["screen_name"]
        isLongText = retweet.get("isLongText", False)
        if isLongText:
            print("Retweet has long text")
            retweetText = retweet["longText"]["longTextContent"]
        else:
            retweetText = retweet["text"]

        if "page_info" in retweet:
            page_info = retweet.get("page_info")
            if page_info.get("type", None) == "video":
                videoURL = page_info["urls"].get("mp4_hd_mp4", None)
                haveVideo = True
    else:
        print("this is not a retweet")

        if "page_info" in weibo:
            page_info = weibo.get("page_info")
            if page_info.get("type", None) == "video":
                videoURL = page_info["urls"].get("mp4_hd_mp4", None)
                haveVideo = True

    result = {
        "originalText": originalText,
        "videoURL": videoURL,
        "retweetText": retweetText,
        "retweetUser": retweetUser,
        "haveVideo": haveVideo,
    }
    return result


class Tweet:
    def __init__(self, tweet_json):
        user = tweet_json["user"]
        self.user = user.get("screen_name", "Undefined")
        self.profileurl = user.get("profile_url", "Undefined")
        self.pics = tweet_json.get("pic_urls", [])
        self.id = tweet_json.get("id", None)
        self.parse_result = parseContent(BSURL + str(self.id))
        self.originalText = self.parse_result["originalText"]
        self.videoURL = self.parse_result["videoURL"]
        self.haveVideo = self.parse_result["haveVideo"]

    def contain_pics(self):
        return len(self.pics) > 0

    def is_retweet(self):
        return isinstance(self, Retweet)

    def debug(self):
        print(
            f"Username:{self.user} Contains pic:{self.contain_pics()} IsRetweet:{self.is_retweet()}"
        )
        print(self.originalText)
        if self.contain_pics():
            print(f"Pics {self.pics}")

    # Publish tweet to tumblr

    def download_pic(self, pics):
        data = []
        for pic in pics:
            url = pic.get("thumbnail_pic", None)
            if url is not None:
                url = url.replace("thumbnail", "original")
                filename = url.split("/")[-1]  # Get file name
                print(f"Download file {filename}")
                obj = session.get(url, allow_redirects=True)
                with open("/tmp/" + filename, "wb") as f:
                    f.write(obj.content)
                data.append("/tmp/" + filename)
        return data

    def publish_to_tumblr(self):
        info = TUMBLR_CLIENT.info()
        try:
            blogName = info.get("user").get("blogs")[0].get("name")
        except KeyError as e:
            print(str(e))
            print("Can not find tumblr blog,exiting")
            sys.exit(1)

        if len(self.pics) != 0:
            # This is a pic tweet, use pic mode
            print("this is a pic tweet")
            data = self.download_pic(self.pics)
            # Construct tweet:
            # Wrap orignText with a div
            tweet_a_tag = (
                f"""<a href="{"https://weibo.com/"+self.profileurl}">{self.user}:</a>"""
            )
            tweet = "<div>" + tweet_a_tag + self.originalText + "</div>"
            TUMBLR_CLIENT.create_photo(
                blogName,
                state="published",
                tags=["weibo"],
                data=data,
                format="html",
                caption=tweet,
            )

            # Cleanup: Delete photos in /tmp folder
            for file in data:
                if os.path.exists(file):
                    os.remove(file)
                else:
                    print(f"File {file} does not exist")
            return

        if self.haveVideo:
            videoURL = self.videoURL
            obj = session.get(videoURL, allow_redirects=True)
            print("This is a video tweet,downloading video from weibo")
            with open("/tmp/" + "video.mp4", "wb") as f:
                f.write(obj.content)
            print("Uploading video to streamable...")
            try:
                with open("/tmp/" + "video.mp4", "rb") as f:
                    files = {"file": f}
                    r = requests.post(STREAMABLE_URL, auth=STREAMABLE_AUTH, files=files)
                    shortcode = r.json().get("shortcode", None)
                    if r.status_code == 200 and shortcode is not None:
                        embed = session.get(
                            "https://api.streamable.com/oembed.json?url=https://streamable.com/"
                            + shortcode
                        )
                        if embed.status_code == 200:
                            print("Posting video to tumblr...")
                            html = embed.json().get("html", "")
                            tweet_a_tag = f"""<a href="{"https://weibo.com/"+self.profileurl}">{self.user}:</a>"""
                            tweet = "<div>" + tweet_a_tag + self.originalText + "</div>"
                            TUMBLR_CLIENT.create_video(
                                blogName, caption=tweet, format="html", embed=html
                            )
                        else:
                            print("Error getting html embed code for video,exiting")
                            sys.exit(1)
                    else:
                        print("Error uploading,exiting...")
                        sys.exit(1)
            except FileNotFoundError as e:
                print(str(e))
                print("No file to upload,exiting...")
                sys.exit(1)
            # Cleanup: Delete photos in /tmp folder
            if os.path.exists("/tmp/" + "video.mp4"):
                os.remove("/tmp/" + "video.mp4")
            else:
                print(f"Video file does not exist")
            return

        # Assume puretext weibo
        tweet_a_tag = (
            f"""<a href="{"https://weibo.com/"+self.profileurl}">{self.user}:</a>"""
        )
        tweet = "<div>" + tweet_a_tag + self.originalText + "</div>"
        TUMBLR_CLIENT.create_text(
            blogName, state="published", tags=["weibo"], format="html", body=tweet
        )


class Retweet(Tweet):
    def __init__(self, tweet_json):
        super(Retweet, self).__init__(tweet_json)
        retweet = tweet_json["retweeted_status"]
        self.pics = retweet.get("pic_urls", [])
        self.retweetUserUrl = retweet["user"]["profile_url"]
        self.retweetText = self.parse_result["retweetText"]
        self.retweetUser = self.parse_result["retweetUser"]

    def debug(self):
        super(Retweet, self).debug()
        print(self.retweetText)
        print(self.retweetUser)

    # TODO: Impl a override function that use bs to parse m.weibo.cn page and grab retweet video link

    def publish_to_tumblr(self):
        info = TUMBLR_CLIENT.info()
        try:
            blogName = info.get("user").get("blogs")[0].get("name")
        except KeyError as e:
            print(str(e))
            print("Can not find tumblr blog,exiting")
            sys.exit(1)

        if len(self.pics) != 0:
            # This is a pic tweet, use pic mode
            print("This is a pic retweet")
            data = self.download_pic(self.pics)

            # Construct tweet:
            # Wrap orignText with a div
            tweet_a_tag = (
                f"""<a href="{"https://weibo.com/"+self.profileurl}">{self.user}:</a>"""
            )
            tweet = "<div>" + tweet_a_tag + self.originalText + "</div>"
            # Wrap retweetText with a div
            retweet_a_tag = f"""<a href="{"https://weibo.com/"+self.retweetUserUrl}">{self.retweetUser}:</a>"""
            retweet = "<div>" + retweet_a_tag + self.retweetText + "</div>"

            TUMBLR_CLIENT.create_photo(
                blogName,
                state="published",
                tags=["testing", "ok"],
                data=data,
                format="html",
                caption=tweet + retweet,
            )
            # Cleanup: Delete photos in /tmp folder
            for file in data:
                if os.path.exists(file):
                    os.remove(file)
                else:
                    print(f"File {file} does not exist")
            return

        if self.haveVideo:
            videoURL = self.videoURL
            obj = session.get(videoURL, allow_redirects=True)
            print("This is a video tweet,downloading video from weibo")
            with open("/tmp/" + "video.mp4", "wb") as f:
                f.write(obj.content)
            print("Uploading video to streamable...")

            try:
                with open("/tmp/" + "video.mp4", "rb") as f:
                    files = {"file": f}
                    r = requests.post(STREAMABLE_URL, auth=STREAMABLE_AUTH, files=files)
                    shortcode = r.json().get("shortcode", None)
                    if r.status_code == 200 and shortcode is not None:
                        embed = session.get(
                            "https://api.streamable.com/oembed.json?url=https://streamable.com/"
                            + shortcode
                        )
                        if embed.status_code == 200:
                            print("Posting video to tumblr...")
                            html = embed.json().get("html", "")
                            tweet_a_tag = f"""<a href="{"https://weibo.com/"+self.profileurl}">{self.user}:</a>"""
                            tweet = "<div>" + tweet_a_tag + self.originalText + "</div>"
                            retweet_a_tag = f"""<a href="{"https://weibo.com/"+self.retweetUserUrl}">{self.retweetUser}:</a>"""
                            retweet = (
                                "<div>" + retweet_a_tag + self.retweetText + "</div>"
                            )
                            TUMBLR_CLIENT.create_video(
                                blogName,
                                caption=tweet + retweet,
                                format="html",
                                embed=html,
                            )
                        else:
                            print("Error getting html embed code for video,exiting")
                            sys.exit(1)
                    else:
                        print("Error uploading,exiting...")
                        sys.exit(1)
            except FileNotFoundError as e:
                print(str(e))
                print("No file to upload,exiting...")
                sys.exit(1)
            # Cleanup: Delete photos in /tmp folder
            if os.path.exists("/tmp/" + "video.mp4"):
                os.remove("/tmp/" + "video.mp4")
            else:
                print(f"Video file does not exist")
            return

        # Assume puretext weibo
        tweet_a_tag = (
            f"""<a href="{"https://weibo.com/"+self.profileurl}">{self.user}:</a>"""
        )
        tweet = "<div>" + tweet_a_tag + self.originalText + "</div>"
        retweet_a_tag = f"""<a href="{"https://weibo.com/"+self.retweetUserUrl}">{self.retweetUser}:</a>"""
        retweet = "<div>" + retweet_a_tag + self.retweetText + "</div>"
        TUMBLR_CLIENT.create_text(
            blogName,
            state="published",
            tags=["weibo"],
            format="html",
            body=tweet + retweet,
        )


def weiboToTumblr(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <http://flask.pocoo.org/docs/1.0/api/#flask.Request>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>.
    """
    content_type = request.headers["content-type"]
    if content_type == "application/json":
        request_json = request.get_json(silent=True)
        if request_json and "weiboURL" in request_json:
            weiboURL = request_json["weiboURL"]
    else:
        raise ValueError("Unknown content type: {}".format(content_type))
    tweetID = weiboURL.split("id=")[-1]
    payload = {"access_token": API_KEY, "id": tweetID}
    r = session.get(URL, params=payload)
    tweet_json = r.json()

    if "retweeted_status" in tweet_json:
        tweet = Retweet(tweet_json)
    else:
        tweet = Tweet(tweet_json)

    # tweet.debug()
    tweet.publish_to_tumblr()

    return "Success"
