import argparse
import requests
import sqlite3
import json
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import os

NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')

DB_FILE = 'news_aggregator.db'
JSON_FILE = 'news_results.json'

NEWS_SOURCES = {
    'newsapi': 'https://newsapi.org/v2/top-headlines',
    'bbc': 'https://www.bbc.com/news',
    'cnn': 'https://edition.cnn.com/world',
}

def fetch_newsapi_headlines(keyword=None, date=None):
    params = {
        'apiKey': NEWSAPI_KEY,
        'q': keyword,
        'from': date,
        'language': 'en',
        'pageSize': 100,
    }
    response = requests.get(NEWS_SOURCES['newsapi'], params=params)
    articles = response.json().get('articles', [])
    return [
        {
            'source': 'newsapi',
            'title': a['title'],
            'url': a['url'],
            'publishedAt': a['publishedAt'],
        } for a in articles if a.get('title')
    ]

def fetch_bbc_headlines():
    response = requests.get(NEWS_SOURCES['bbc'])
    soup = BeautifulSoup(response.text, 'html.parser')
    headlines = []
    for item in soup.select('h3'):  # BBC headlines
        title = item.get_text(strip=True)
        if title:
            headlines.append({'source': 'bbc', 'title': title, 'url': NEWS_SOURCES['bbc'], 'publishedAt': datetime.now().isoformat()})
    return headlines

def fetch_cnn_headlines():
    response = requests.get(NEWS_SOURCES['cnn'])
    soup = BeautifulSoup(response.text, 'html.parser')
    headlines = []
    for item in soup.select('span.cd__headline-text'):  # CNN headlines
        title = item.get_text(strip=True)
        if title:
            headlines.append({'source': 'cnn', 'title': title, 'url': NEWS_SOURCES['cnn'], 'publishedAt': datetime.now().isoformat()})
    return headlines

def deduplicate(headlines):
    seen = set()
    deduped = []
    for h in headlines:
        key = (h['title'], h['source'])
        if key not in seen:
            deduped.append(h)
            seen.add(key)
    return deduped

def store_to_json(headlines):
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(headlines, f, indent=2)

def store_to_sqlite(headlines):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS headlines (source TEXT, title TEXT, url TEXT, publishedAt TEXT)''')
    for h in headlines:
        c.execute('INSERT INTO headlines VALUES (?, ?, ?, ?)', (h['source'], h['title'], h['url'], h['publishedAt']))
    conn.commit()
    conn.close()

def export_csv(headlines, filename='news_results.csv'):
    df = pd.DataFrame(headlines)
    df.to_csv(filename, index=False)

def export_excel(headlines, filename='news_results.xlsx'):
    df = pd.DataFrame(headlines)
    df.to_excel(filename, index=False)

def filter_headlines(headlines, source=None, keyword=None, date=None):
    filtered = headlines
    if source:
        filtered = [h for h in filtered if h['source'] == source]
    if keyword:
        filtered = [h for h in filtered if keyword.lower() in h['title'].lower()]
    if date:
        filtered = [h for h in filtered if h['publishedAt'][:10] == date]
    return filtered

def main():
    parser = argparse.ArgumentParser(description='News Aggregator CLI')
    parser.add_argument('--source', choices=['newsapi', 'bbc', 'cnn', 'all'], default='all', help='News source')
    parser.add_argument('--keyword', help='Keyword filter')
    parser.add_argument('--date', help='Date filter (YYYY-MM-DD)')
    parser.add_argument('--store', choices=['json', 'sqlite'], help='Store results')
    parser.add_argument('--export', choices=['csv', 'excel'], help='Export results')
    args = parser.parse_args()

    headlines = []
    if args.source in ['all', 'newsapi']:
        headlines += fetch_newsapi_headlines(args.keyword, args.date)
    if args.source in ['all', 'bbc']:
        headlines += fetch_bbc_headlines()
    if args.source in ['all', 'cnn']:
        headlines += fetch_cnn_headlines()

    headlines = deduplicate(headlines)
    headlines = filter_headlines(headlines, args.source if args.source != 'all' else None, args.keyword, args.date)

    if args.store == 'json':
        store_to_json(headlines)
    elif args.store == 'sqlite':
        store_to_sqlite(headlines)

    if args.export == 'csv':
        export_csv(headlines)
    elif args.export == 'excel':
        export_excel(headlines)

    for h in headlines:
        print(f"[{h['source']}] {h['title']} ({h['publishedAt']})")

if __name__ == '__main__':
    main()