from youtubesearchpython import VideosSearch
from googleapiclient.errors import HttpError
import googleapiclient.discovery
import googleapiclient.errors
import logging
import time
from typing import List

# Needed to lookup video metadata, anyway this API is very cheap and we can
# lookup 10k ids per day per key. Search API is much more expensive and we
# can only do 100 searches per day per key, hence we use VideoSearch
# library for "unlimited" searches.
# To get the api key use: https://developers.google.com/youtube/v3/getting-started
YT_API_KEYS = ()

class FreeQuotaYtClient:
    def __init__(self, api_keys=YT_API_KEYS):
        self.api_keys = list(api_keys)
        if not self.api_keys:
            raise ValueError("No YT api keys provided, please get at least one via https://developers.google.com/youtube/v3/getting-started")
        self.yt = None
        self.init_new_yt()

    def init_new_yt(self):
        if not self.api_keys:
            raise ValueError("Run out of api keys :(")
        api_key = self.api_keys.pop()
        print("using api key", api_key)
        self.yt = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)

    def get(self, resource, method):
        def wrapper(*args, **kwargs):
            while 1:
                meth = getattr(getattr(self.yt, resource)(), method)
                try:
                    return meth(*args, **kwargs).execute()
                except HttpError as e:
                    if e.resp.status == 403:
                        logging.warning("Run out of quota, using new api key, before that sleeping for 10 seconds...")
                        time.sleep(10)
                        self.init_new_yt()
                    else:
                        raise
        return wrapper


def query_video_details(youtube_search_query: str, youtube_client: FreeQuotaYtClient, force_captions=False, use_yt_search_api=False) -> List[dict]:

    """
    Returns a list of youtube video details for a given youtube search query. About 20 top results are returned.
    force_captions: forces the results to be captioned (only works if use_yt_search_api is True)
    use_yt_search_api: whether to use official youtube search api, more reliable, but will quickly run out of quota.

    Example detail:
     {
            "etag": "MO7INtQBp2b0E8_bnmJ4I76mtPU",
            "id": "bYu-T2hgOb4",
            "kind": "youtube#video",
            "snippet": {
                "categoryId": "29",
                "channelId": "UCsT0YIqwnpJCM-mx7-gSA4Q",
                "channelTitle": "TEDx Talks",
                "defaultAudioLanguage": "en",
                "description": "A breathtaking speech about the reasons why human evolution can either spiral upward or collapse on itself if the past isn't constantly explored and conserved in order to build upon it. Riveting.  This talk was given at a TEDx event using the TED conference format but independently organized by a local community. Learn more at https://www.ted.com/tedx",
                "liveBroadcastContent": "none",
                "localized": {
                    "description": "A breathtaking speech about the reasons why human evolution can either spiral upward or collapse on itself if the past isn't constantly explored and conserved in order to build upon it. Riveting.  This talk was given at a TEDx event using the TED conference format but independently organized by a local community. Learn more at https://www.ted.com/tedx",
                    "title": "Calcium Hydroxide the material that immortalized human kind. | Daniela Murphy | TEDxLUCCA"
                },
                "publishedAt": "2019-02-28T18:38:27Z",
                "tags": [
                    "TEDxTalks",
                    "English",
                    "Art"
                ],
                "thumbnails": {
                    "default": {
                        "height": 90,
                        "url": "https://i.ytimg.com/vi/bYu-T2hgOb4/default.jpg",
                        "width": 120
                    },
                },
                "title": "Calcium Hydroxide the material that immortalized human kind. | Daniela Murphy | TEDxLUCCA"
            }
        }
    """
    if not use_yt_search_api:
        vid_ids = [e["id"] for e in VideosSearch(youtube_search_query, limit=20).result()["result"]]
    else:
        search_response = youtube_client.get("search", "list")(
            part="snippet",
            maxResults=50,
            q=youtube_search_query,
            type="video",
            videoCaption="closedCaption" if force_captions else "any"
        )
        vid_ids = [vid["id"]["videoId"] for vid in search_response["items"]]
    if not vid_ids:
        return []
    details = youtube_client.get("videos", "list")(
        part=["snippet", "contentDetails"],
        id=vid_ids
    )["items"]
    assert len(details) == len(vid_ids), (len(details), len(vid_ids))
    return details

if __name__ == '__main__':
    youtube_client =FreeQuotaYtClient()
    print(query_video_details("hello world", youtube_client))
