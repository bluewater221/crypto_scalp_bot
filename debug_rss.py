import feedparser
from datetime import datetime
import time

url = "https://airdropalert.com/feed/rssfeed"
print(f"Parsing {url}...")
feed = feedparser.parse(url)

print(f"Feed Title: {feed.feed.get('title')}")
print(f"Entries found: {len(feed.entries)}")

for i, entry in enumerate(feed.entries[:5]):
    print(f"\n--- Entry {i+1} ---")
    print(f"Title: {entry.title}")
    print(f"Link: {entry.link}")
    pub = entry.get('published')
    pub_parsed = entry.get('published_parsed')
    print(f"Published (raw): {pub}")
    if pub_parsed:
        dt = datetime.fromtimestamp(time.mktime(pub_parsed))
        print(f"Published (parsed): {dt}")
        now = datetime.now()
        diff = now - dt
        print(f"Age: {diff}")
    else:
        print("Published date not parseable.")
