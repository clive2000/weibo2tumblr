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
2. Tumblr API key (Apply your own at https://api.tumblr.com)
3. ifttt account (Sign up at http://ifttt.com)
4. Streamable account (Sign up at https://streamable.com/)
5. Google Cloud Compute Account (Sign up at https://cloud.google.com/)

Weibo API is needed to retrive tweet content from Sina weibo. Tumblr API is needed to post content on tumblr. **ifttt** is required to trigger the cloud function through its webhook applet. **Streamable** is used to upload videos for video tweet and generate embed html. **GCE** accounted is required to deploy this cloud function. You may read more about cloud function at https://cloud.google.com/functions/

## Deployment