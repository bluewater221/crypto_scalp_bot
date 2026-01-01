
import time

print("Start Imports")
start = time.time()

print("Importing requests...")
import requests
print(f"requests: {time.time()-start:.2f}s")

print("Importing yfinance...")
import yfinance as yf
print(f"yfinance: {time.time()-start:.2f}s")

print("Importing feedparser...")
import feedparser
print(f"feedparser: {time.time()-start:.2f}s")

print("Importing textblob...")
from textblob import TextBlob
print(f"textblob: {time.time()-start:.2f}s")

print("Importing google.generativeai...")
import google.generativeai as genai
print(f"google.generativeai: {time.time()-start:.2f}s")

print("Importing news_manager...")
import news_manager
print(f"news_manager: {time.time()-start:.2f}s")
