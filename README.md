# weibo2tumblr
A serverless function to cross-post from Sina Weibo to Tumblr

## Motivation

On the Sina weibo, it is common for your tweet/retweet to be deleted by mods or original poster. Thus I would be great to have a tool that simultaneously sync your post to another microblog platform. 

Preferably, whenever I post a Weibo tweet, an event will trigger my app to post the same content on tumblr. I could write an app in python and wrap it in a docker container. However, I don't have any spare server that is on 24 hours a day. I decide to host it as a serverless application on Google Cloud Functions (Google Cloud Compute component)

## Why cross-post to tumblr(not twitter)?

1. Tumblr supports uploading multiple photos in a single post, so your weibo retweet with mulitple photos could be display in a single tumblr post.

2. Tumblr supports html in the post, so all html parsed in Sina weibo content could be used directly in the tumblr post.

3. Since tumblr supports html in the post, you can easily embed videos(from streamable) in the post. This means we can also sync video post between Sina weibo and tmublr.

## Requirements

1. Weibo API key (Apply your own at https://open.weibo.com)
2. Tumblr API key (Apply your own at https://www.tumblr.com/oauth/apps)
3. ifttt account (Sign up at http://ifttt.com)
4. Streamable account (Sign up at https://streamable.com/)
5. Google Cloud Compute Account (Sign up at https://cloud.google.com/)

Weibo API is needed to retrive tweet content from Sina weibo. Tumblr API is needed to post content on tumblr. **ifttt** is required to trigger the cloud function through its webhook applet. **Streamable** is used to upload videos for video tweet and generate embed html. **GCE** accounte is required to deploy this cloud function. You can read more about cloud function at https://cloud.google.com/functions/

## Deployment

0. Clone this git repo. In the repo, create a python virtualenv.

```bash
virtualenv --python python3 env
pip install -r requirements.txt
source ./env/bin/activate
```

1. In *main.py*, replace `API_KEY` with your Sina weibo API Key, Reokace `consumer_key`,`consumer_secret`,`oauth_token`,`oauth_secret` with your tumblr oath information. Replace `EMAIL`,`PASSWORD` in `STREAMABLE_AUTH = HTTPBasicAuth('<EMAIL>', '<PASSWORD>')` with your streamable credentials. 

2. Install and set up gcloud in your operating system. You can follow the guide at https://cloud.google.com/sdk/docs/quickstart-linux

3. Deploy the cloud functions using gcloud cli:

```bash
gcloud functions deploy weiboToTumblr --runtime python37 --trigger-http --memory=512MB
```

4. After function is deployed, you will get a http entrypoint, it looks like this:

```
httpsTrigger:
  url: https://<REGION-PROJECTID-FUNCTIONID>.cloudfunctions.net/weiboToTumblr
```

5. In ifttt, create a applet. **This** part will be "Sina Weibo - New post by you" **That** part will be "Webhook - Make a web request". In the setting of webhook, put the http entry point you get in step 4 into URL field. Set method to **POST**. Set Content Type to **application/json**. Set body to `{"weiboURL": " {{WeiboURL}}"}` Finally, hit create actions. 

That's it! When you post a new Weibo Tweet, ifttt will send a HTTP POST request to your cloud fucntion. The cloud function will then look into your Weibo post and cross-post the content on Tumblr.

## Cost

Check https://cloud.google.com/functions/pricing for cloud function's pricing. For me the cost of this function is an absolute $0 per month. The first 2 million invocations of cloud function is free. For me it will never be possible to post 2 million tweets per month. Cloud function then charges for the computing resorces used by the function. I chose to provision the function on a 512MB instance. And each month I get 400,000 GB-seconds, 200,000 GHz-seconds of compute time for free. That means the function could be run 800,0000 seconds for free each montn, which far exceeds the running time of the function. 

## TODOs

1. Refactor the code, I wrote the python code in a rush. Definitely the code could be refactored for better readability. 
2. Find a better way to pharse weibo post. Right now I am using BeautifulSoup to parse weibo content on https://m.weibo.cn domain. This is Sina weibo's mobile friendly site and photos and videos could be easily parsed from this domain. However the might change that later so BS4 wouldn't be able to parse content fron m.weibo.cn. And that will break this cloud function. I need to look into other ways to parse Weibo post content.
