#!/usr/bin/env python3
"""
Data seeding script for pg_trgm fuzzy search demo.
Scrapes data from Wikipedia and OpenLibrary API, then inserts into PostgreSQL.
"""

import requests
from bs4 import BeautifulSoup
import psycopg2
import time
import re
import xml.etree.ElementTree as ET
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import urllib3

# Disable SSL warnings for APIs with certificate issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Database connection parameters
DB_PARAMS = {
    'host': 'localhost',
    'port': 5432,
    'database': 'testdb',
    'user': 'postgres',
    'password': 'password'
}

def scrape_wikipedia_books():
    """Scrape best-selling books from Wikipedia using batch API (optimized)"""
    start_time = time.time()
    print("\nScraping Wikipedia best-selling books...")
    print("  → Fetching list page...", end=' ', flush=True)
    url = "https://en.wikipedia.org/wiki/List_of_best-selling_books"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print("✓")
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # First pass: collect all titles
        print("  → Collecting book titles...", end=' ', flush=True)
        titles = []
        tables = soup.find_all('table', {'class': 'wikitable'})
        
        for table in tables[:3]:  # Process first 3 tables
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows[:30]:  # Limit per table
                cells = row.find_all(['td', 'th'])
                if len(cells) < 1:
                    continue
                
                # Get book title from first column
                first_cell = cells[0]
                link = first_cell.find('a')
                
                if link and link.get('href'):
                    title = link.get_text(strip=True)
                    # Clean up title
                    title = re.sub(r'\[.*?\]', '', title).strip()
                    
                    if title and len(title) > 2:
                        titles.append(title)
                
                if len(titles) >= 50:
                    break
            
            if len(titles) >= 50:
                break
        
        print(f"Found {len(titles)} titles")
        
        # Second pass: batch fetch descriptions using Wikipedia API
        # This is MUCH faster - only 1 request instead of 50!
        print(f"  → Batch fetching descriptions (1 request for all {len(titles)} books)...", end=' ', flush=True)
        books = []
        
        # Wikipedia API can handle up to 50 titles per request
        batch_size = 50
        for i in range(0, len(titles), batch_size):
            batch_titles = titles[i:i+batch_size]
            
            api_url = "https://en.wikipedia.org/w/api.php"
            params = {
                'action': 'query',
                'format': 'json',
                'titles': '|'.join(batch_titles),  # Join titles with |
                'prop': 'extracts',
                'exintro': True,  # Only intro section
                'explaintext': True,  # Plain text
                'exsentences': 3  # First 3 sentences
            }
            
            api_response = requests.get(api_url, params=params, headers=headers, timeout=15)
            if api_response.status_code == 200:
                data = api_response.json()
                pages = data.get('query', {}).get('pages', {})
                
                for page_id, page_data in pages.items():
                    if page_id == '-1':  # Page not found
                        continue
                    title = page_data.get('title', '')
                    extract = page_data.get('extract', '')
                    if title and extract and len(extract) > 50:
                        # Limit description length
                        books.append((title, extract[:500]))
        
        print(f"✓ Got {len(books)} descriptions")
        elapsed_time = time.time() - start_time
        print(f"✓ Total: {len(books)} books from Wikipedia (optimized: 2 requests vs 51 before)")
        print(f"⏱️  Time taken: {elapsed_time:.2f} seconds")
        return books
    
    except Exception as e:
        print(f"\n✗ Error scraping Wikipedia: {e}")
        return []

def scrape_arxiv_papers(target_count=4000, max_workers=5):
    """
    Scrape academic papers from ArXiv API with parallel processing.
    Returns papers with title and abstract (description).
    """
    start_time = time.time()
    print(f"\nScraping ArXiv papers (Target: {target_count}, Parallel workers: {max_workers})...")
    papers = []
    seen_titles = set()
    lock = threading.Lock()  # Thread-safe operations
    
    # ArXiv categories - diverse fields
    categories = [
        'cs.AI', 'cs.LG', 'cs.CL', 'cs.CV', 'cs.NE', 'cs.RO',  # Computer Science
        'physics:cond-mat', 'physics:astro-ph', 'physics:hep-th',  # Physics
        'math.CO', 'math.AG', 'math.NT',  # Mathematics
        'q-bio.GN', 'q-bio.NC',  # Quantitative Biology
        'stat.ML', 'econ.EM'  # Statistics & Economics
    ]
    
    def fetch_arxiv_batch(category, start, batch_num):
        """Fetch a single batch from ArXiv"""
        try:
            url = f'http://export.arxiv.org/api/query?search_query=cat:{category}&start={start}&max_results=100'
            response = requests.get(url, timeout=15)
            
            if response.status_code != 200:
                return []
            
            # Parse XML response
            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', ns)
            
            batch_papers = []
            for entry in entries:
                title_elem = entry.find('atom:title', ns)
                summary_elem = entry.find('atom:summary', ns)
                
                if title_elem is not None and summary_elem is not None:
                    title = title_elem.text.replace('\n', ' ').strip()
                    summary = summary_elem.text.replace('\n', ' ').strip()
                    
                    if len(summary) > 100:
                        batch_papers.append((title, summary))
            
            return batch_papers
            
        except Exception as e:
            print(f"\n    ✗ Error in batch {batch_num}: {e}")
            return []
    
    # Process categories
    for idx, category in enumerate(categories, 1):
        with lock:
            if len(papers) >= target_count:
                print(f"  ✓ Target reached! Skipping remaining categories...")
                break
        
        print(f"  [{idx}/{len(categories)}] Category: {category} - Parallel fetching...", end=' ', flush=True)
        category_start = len(papers)
        
        # Create tasks for parallel execution
        tasks = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for batch_num, start in enumerate(range(0, 500, 100), 1):
                if len(papers) >= target_count:
                    break
                future = executor.submit(fetch_arxiv_batch, category, start, batch_num)
                tasks.append(future)
            
            # Collect results as they complete
            for future in as_completed(tasks):
                batch_papers = future.result()
                
                with lock:
                    for title, summary in batch_papers:
                        title_lower = title.lower()
                        if title_lower not in seen_titles:
                            seen_titles.add(title_lower)
                            papers.append((title, summary))
                            
                            if len(papers) >= target_count:
                                break
        
        category_added = len(papers) - category_start
        print(f"✓ Added {category_added}, Total: {len(papers)}/{target_count}")
        
        # Brief pause between categories
        time.sleep(0.5)
    
    elapsed_time = time.time() - start_time
    print(f"✓ Total ArXiv papers collected: {len(papers)}")
    print(f"⏱️  Time taken: {elapsed_time:.2f} seconds")
    return papers

def scrape_wikipedia_bulk(target_count=4000, max_workers=30):
    """
    Scrape random Wikipedia articles using optimized batch API.
    Uses list=random (500 IDs) + batch content fetch (50 per request).
    Much faster: ~400-450 articles per 11 requests vs ~15-18 per request.
    """
    start_time = time.time()
    print(f"\nScraping Wikipedia articles (Target: {target_count}, Parallel workers: {max_workers})...")
    articles = []
    seen_titles = set()
    lock = threading.Lock()
    
    def fetch_wikipedia_batch_optimized():
        """
        Optimized: Fetch 500 random page IDs, then batch query content.
        Returns ~400-450 articles per call (vs ~15-18 before).
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # Step 1: Get 500 random page IDs
            url = "https://en.wikipedia.org/w/api.php"
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'random',
                'rnnamespace': 0,
                'rnlimit': 500  # Max 500 random pages
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            if response.status_code != 200:
                return []
            
            data = response.json()
            random_pages = data.get('query', {}).get('random', [])
            page_ids = [str(page['id']) for page in random_pages]
            
            if not page_ids:
                return []
            
            # Step 2: Batch fetch content (50 pages per request, max limit)
            batch_articles = []
            for i in range(0, len(page_ids), 50):
                batch_ids = page_ids[i:i+50]
                
                content_params = {
                    'action': 'query',
                    'format': 'json',
                    'pageids': '|'.join(batch_ids),
                    'prop': 'extracts',
                    'exintro': True,
                    'explaintext': True,
                    'exsentences': 5
                }
                
                content_response = requests.get(url, params=content_params, headers=headers, timeout=15)
                if content_response.status_code != 200:
                    continue
                
                content_data = content_response.json()
                pages = content_data.get('query', {}).get('pages', {})
                
                for page_id, page_data in pages.items():
                    title = page_data.get('title', '')
                    extract = page_data.get('extract', '')
                    
                    # Relaxed filter: 50 chars (was 100)
                    if (title and extract and 
                        len(extract) > 50 and
                        'may refer to' not in extract):
                        batch_articles.append((title, extract))
            
            return batch_articles
            
        except Exception as e:
            return []
    
    # Calculate batches needed (each batch now gets ~180-200 articles on average)
    # Conservative estimate to ensure we reach target
    batches_needed = (target_count // 180) + 3
    
    print(f"  → Launching {batches_needed} parallel super-batches (each fetches ~180-200 articles)...", flush=True)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit tasks
        futures = [executor.submit(fetch_wikipedia_batch_optimized) for _ in range(batches_needed)]
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(futures):
            batch_articles = future.result()
            completed += 1
            
            with lock:
                for title, extract in batch_articles:
                    title_lower = title.lower()
                    if title_lower not in seen_titles:
                        seen_titles.add(title_lower)
                        articles.append((title, extract))
                        
                        if len(articles) >= target_count:
                            break
                
                # Show progress
                progress_pct = (len(articles) / target_count) * 100
                print(f"  📊 Super-batch {completed}/{batches_needed} complete, Articles: {len(articles)}/{target_count} ({progress_pct:.1f}%)")
                
                if len(articles) >= target_count:
                    break
    
    elapsed_time = time.time() - start_time
    print(f"✓ Total Wikipedia articles collected: {len(articles)} (Optimized: ~25x faster)")
    print(f"⏱️  Time taken: {elapsed_time:.2f} seconds")
    return articles[:target_count]  # Ensure we don't exceed target

def scrape_google_books_free(target_count=2000, max_workers=5):
    """
    Use Google Books public API to scrape book descriptions with parallel processing.
    Free and no API key required.
    """
    start_time = time.time()
    print(f"\nScraping Google Books (Target: {target_count}, Parallel workers: {max_workers})...")
    books = []
    seen_titles = set()
    lock = threading.Lock()
    
    # Expanded list of subjects for more diversity
    subjects = [
        'fiction', 'history', 'science', 'programming', 'art', 'cooking', 'travel', 
        'fantasy', 'mystery', 'philosophy', 'psychology', 'business', 'economics',
        'medicine', 'biology', 'chemistry', 'physics', 'mathematics', 'engineering',
        'literature', 'poetry', 'drama', 'music', 'architecture', 'photography',
        'religion', 'sociology', 'anthropology', 'education', 'law'
    ]
    
    def fetch_google_books_page(subject, start_index):
        """Fetch a single page of Google Books results"""
        try:
            url = f"https://www.googleapis.com/books/v1/volumes?q=subject:{subject}&startIndex={start_index}&maxResults=40&langRestrict=en"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            items = data.get('items', [])
            
            page_books = []
            for item in items:
                info = item.get('volumeInfo', {})
                title = info.get('title')
                description = info.get('description')
                
                if title and description and len(description) > 50:
                    page_books.append((title, description))
            
            return page_books
            
        except Exception as e:
            return []
    
    for idx, subject in enumerate(subjects, 1):
        with lock:
            if len(books) >= target_count:
                print(f"  ✓ Target reached! Skipping remaining subjects...")
                break
        
        print(f"  [{idx}/{len(subjects)}] Subject: {subject} - Parallel fetching...", end=' ', flush=True)
        subject_start = len(books)
        
        # Create tasks for parallel execution (fetch multiple pages at once)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for start_index in range(0, 200, 40):  # 5 pages per subject
                if len(books) >= target_count:
                    break
                future = executor.submit(fetch_google_books_page, subject, start_index)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                page_books = future.result()
                
                with lock:
                    for title, description in page_books:
                        title_lower = title.lower()
                        if title_lower not in seen_titles:
                            seen_titles.add(title_lower)
                            books.append((title, description))
                            
                            if len(books) >= target_count:
                                break
        
        subject_added = len(books) - subject_start
        print(f"✓ +{subject_added} (Total: {len(books)}/{target_count})")
        
        # Brief pause between subjects to avoid rate limiting
        time.sleep(0.3)
    
    elapsed_time = time.time() - start_time
    print(f"✓ Total Google Books collected: {len(books)}")
    print(f"⏱️  Time taken: {elapsed_time:.2f} seconds")
    return books

def scrape_quotable_quotes(target_count=1500):
    """
    Scrape inspirational quotes from Quotable.io API.
    Free API, no key required (SSL certificate bypass needed).
    """
    start_time = time.time()
    print(f"\nScraping quotes from Quotable.io (Target: {target_count})...")
    quotes = []
    seen_quotes = set()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    attempts = 0
    max_attempts = target_count * 2  # Allow retries
    
    while len(quotes) < target_count and attempts < max_attempts:
        attempts += 1
        
        try:
            url = "https://api.quotable.io/random"
            # Use verify=False to bypass SSL certificate verification
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                author = data.get('author', 'Unknown')
                content = data.get('content', '')
                
                # Check for duplicates and minimum length
                if content and content not in seen_quotes and len(content) > 20:
                    seen_quotes.add(content)
                    title = f"Quote by {author}"
                    description = f'"{content}" - {author}'
                    quotes.append((title, description))
                    
                    if len(quotes) % 100 == 0:
                        print(f"  Progress: {len(quotes)}/{target_count}")
            
            # Rate limiting
            time.sleep(0.2)
            
        except Exception as e:
            # Silent fail, continue to next
            continue
    
    elapsed_time = time.time() - start_time
    print(f"✓ Total quotes collected: {len(quotes)}")
    print(f"⏱️  Time taken: {elapsed_time:.2f} seconds")
    return quotes

def scrape_random_facts(target_count=1000):
    """
    Scrape random interesting facts from UselessFacts API.
    Free API, no key required.
    """
    start_time = time.time()
    print(f"\nScraping random facts from UselessFacts (Target: {target_count})...")
    facts = []
    seen_facts = set()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    attempts = 0
    max_attempts = target_count * 2
    
    while len(facts) < target_count and attempts < max_attempts:
        attempts += 1
        
        try:
            url = "https://uselessfacts.jsph.pl/random.json?language=en"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                fact = data.get('text', '')
                
                # Check for duplicates and minimum length
                if fact and fact not in seen_facts and len(fact) > 20:
                    seen_facts.add(fact)
                    
                    # Generate title from first few words
                    title_words = fact.split()[:8]
                    title = ' '.join(title_words)
                    if len(fact.split()) > 8:
                        title += '...'
                    
                    facts.append((title, fact))
                    
                    if len(facts) % 100 == 0:
                        print(f"  Progress: {len(facts)}/{target_count}")
            
            # Rate limiting
            time.sleep(0.2)
            
        except Exception as e:
            continue
    
    elapsed_time = time.time() - start_time
    print(f"✓ Total facts collected: {len(facts)}")
    print(f"⏱️  Time taken: {elapsed_time:.2f} seconds")
    return facts

def scrape_zenquotes(target_count=500):
    """
    Scrape quotes from ZenQuotes API (alternative quote source).
    Free API, no key required, but has strict rate limit (5 requests per 30 seconds).
    """
    start_time = time.time()
    print(f"\nScraping quotes from ZenQuotes (Target: {target_count})...")
    quotes = []
    seen_quotes = set()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    attempts = 0
    max_attempts = target_count * 2
    request_count = 0
    
    while len(quotes) < target_count and attempts < max_attempts:
        attempts += 1
        
        try:
            url = "https://zenquotes.io/api/random"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    quote = data[0]
                    author = quote.get('a', 'Unknown')
                    content = quote.get('q', '')
                    
                    # Check for duplicates and minimum length
                    if content and content not in seen_quotes and len(content) > 20:
                        seen_quotes.add(content)
                        title = f"Quote by {author}"
                        description = f'"{content}" - {author}'
                        quotes.append((title, description))
                        
                        if len(quotes) % 50 == 0:
                            print(f"  Progress: {len(quotes)}/{target_count}")
            
            # ZenQuotes rate limit: 5 requests per 30 seconds
            request_count += 1
            if request_count % 5 == 0:
                time.sleep(6)  # Wait 6 seconds every 5 requests
            else:
                time.sleep(0.5)
            
        except Exception as e:
            continue
    
    elapsed_time = time.time() - start_time
    print(f"✓ Total ZenQuotes collected: {len(quotes)}")
    print(f"⏱️  Time taken: {elapsed_time:.2f} seconds")
    return quotes

def scrape_openlibrary_books():
    """Scrape books from OpenLibrary API with multiple strategies to get 10,000+ books"""
    print("\nScraping OpenLibrary books (targeting 10,000+ books)...")
    
    books = []
    seen_titles = set()  # Track titles to avoid duplicates during scraping
    
    def add_book(title, description):
        """Helper to add unique books"""
        title_lower = title.lower().strip()
        if title_lower and len(title) >= 2 and title_lower not in seen_titles:
            seen_titles.add(title_lower)
            books.append((title, description))
            if len(books) % 100 == 0:  # Progress update every 100 books
                print(f"  Progress: {len(books)} books collected...")
            return True
        return False
    
    # Strategy 1: Comprehensive subject search with pagination
    subjects = [
        # Fiction genres
        'fantasy', 'science fiction', 'mystery', 'romance', 'thriller',
        'horror', 'historical fiction', 'adventure', 'classics', 'crime',
        'dystopian', 'young adult', 'children', 'comedy', 'action', 'urban fantasy',
        'paranormal', 'steampunk', 'cyberpunk', 'epic fantasy', 'space opera',
        'literary fiction', 'contemporary fiction', 'magical realism',
        # Non-fiction
        'biography', 'autobiography', 'memoir', 'history', 'philosophy', 
        'psychology', 'science', 'nature', 'travel', 'cooking',
        'self-help', 'business', 'politics', 'religion', 'art',
        'music', 'sports', 'health', 'technology', 'education',
        # More specific
        'war', 'love', 'family', 'friendship', 'coming of age',
        'detective', 'spy', 'legal', 'medical', 'western'
    ]
    
    print(f"Strategy 1: Searching {len(subjects)} subjects with pagination...")
    for subject in subjects:
        if len(books) >= 10000:
            break
            
        # Use pagination to get more results per subject
        for offset in [0, 100, 200]:
            if len(books) >= 10000:
                break
                
            try:
                url = f"https://openlibrary.org/search.json?q={subject}&limit=100&offset={offset}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                for doc in data.get('docs', []):
                    title = doc.get('title', '').strip()
                    if not title:
                        continue
                    
                    description = ""
                    if 'first_sentence' in doc and doc['first_sentence']:
                        if isinstance(doc['first_sentence'], list):
                            description = doc['first_sentence'][0]
                        else:
                            description = doc['first_sentence']
                    elif 'author_name' in doc and doc['author_name']:
                        authors = ', '.join(doc['author_name'][:3])
                        description = f"Written by {authors}"
                        if 'first_publish_year' in doc:
                            description += f". First published in {doc['first_publish_year']}"
                    
                    add_book(title, description)
                    
                    if len(books) >= 10000:
                        break
                
                time.sleep(0.3)  # Be polite to API
                
            except Exception as e:
                print(f"  Error on {subject} (offset {offset}): {e}")
                continue
    
    print(f"After Strategy 1: {len(books)} books")
    
    # Strategy 2: Search by popular authors
    if len(books) < 10000:
        print("\nStrategy 2: Searching by popular authors...")
        popular_authors = [
            'stephen king', 'agatha christie', 'jk rowling', 'tolkien',
            'george martin', 'isaac asimov', 'arthur clarke', 'philip dick',
            'ursula le guin', 'neil gaiman', 'terry pratchett', 'brandon sanderson',
            'jane austen', 'charles dickens', 'mark twain', 'hemingway',
            'shakespeare', 'edgar poe', 'lovecraft', 'oscar wilde',
            'george orwell', 'aldous huxley', 'ray bradbury', 'frank herbert',
            'douglas adams', 'haruki murakami', 'margaret atwood', 'kurt vonnegut'
        ]
        
        for author in popular_authors:
            if len(books) >= 10000:
                break
                
            try:
                url = f"https://openlibrary.org/search.json?author={author}&limit=100"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                for doc in data.get('docs', []):
                    title = doc.get('title', '').strip()
                    if not title:
                        continue
                    
                    description = f"Written by {author.title()}"
                    if 'first_publish_year' in doc:
                        description += f". First published in {doc['first_publish_year']}"
                    
                    add_book(title, description)
                    
                    if len(books) >= 10000:
                        break
                
                time.sleep(0.3)
                
            except Exception as e:
                print(f"  Error for author {author}: {e}")
                continue
    
    print(f"After Strategy 2: {len(books)} books")
    
    # Strategy 3: Browse by publication year ranges
    if len(books) < 10000:
        print("\nStrategy 3: Searching by publication decades...")
        decades = [1900, 1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020]
        
        for decade in decades:
            if len(books) >= 10000:
                break
                
            try:
                url = f"https://openlibrary.org/search.json?q=*&publish_year={decade}&limit=100"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                for doc in data.get('docs', []):
                    title = doc.get('title', '').strip()
                    if not title:
                        continue
                    
                    description = ""
                    if 'author_name' in doc and doc['author_name']:
                        authors = ', '.join(doc['author_name'][:2])
                        description = f"Written by {authors}. Published around {decade}"
                    else:
                        description = f"Published around {decade}"
                    
                    add_book(title, description)
                    
                    if len(books) >= 10000:
                        break
                
                time.sleep(0.3)
                
            except Exception as e:
                print(f"  Error for decade {decade}: {e}")
                continue
    
    print(f"\nFinal count: {len(books)} books from OpenLibrary")
    return books

def create_database_if_not_exists():
    """Create the database and table if they don't exist"""
    print("Checking database...")
    sys_params = DB_PARAMS.copy()
    sys_params['database'] = 'postgres'
    
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(**sys_params)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if testdb exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_PARAMS['database'],))
        if not cur.fetchone():
            print(f"Creating database {DB_PARAMS['database']}...")
            cur.execute(f"CREATE DATABASE {DB_PARAMS['database']}")
        
        cur.close()
        conn.close()
        
        # Now connect to testdb and create schema
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # Read init.sql
        try:
            with open('init.sql', 'r') as f:
                sql = f.read()
                cur.execute(sql)
            conn.commit()
            print("Database schema initialized.")
        except FileNotFoundError:
            # Fallback if init.sql is missing
            print("init.sql not found, creating schema manually...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS worlds (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT
                )
            """)
            conn.commit()
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Database setup error: {e}")

def insert_books_to_db(books):
    """Insert books into PostgreSQL database"""
    print("\n" + "="*60)
    print("DATABASE OPERATIONS")
    print("="*60)
    
    try:
        print("→ Connecting to PostgreSQL...", end=' ', flush=True)
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        print("✓")
        
        print("→ Clearing existing data...", end=' ', flush=True)
        cur.execute("DELETE FROM worlds")
        conn.commit()
        print("✓")
        
        print(f"→ Inserting {len(books)} records...")
        batch_size = 100
        for i in range(0, len(books), batch_size):
            batch = books[i:i+batch_size]
            for title, description in batch:
                cur.execute(
                    "INSERT INTO worlds (title, description) VALUES (%s, %s)",
                    (title, description)
                )
            conn.commit()
            progress = min(i + batch_size, len(books))
            progress_pct = (progress / len(books)) * 100
            print(f"  Progress: {progress}/{len(books)} ({progress_pct:.1f}%)")
        
        # Get count
        cur.execute("SELECT COUNT(*) FROM worlds")
        count = cur.fetchone()[0]
        print(f"✓ Successfully inserted {count} records")
        
        # Create trigram indexes
        print("\n→ Creating trigram indexes (this may take a moment)...")
        print("  Dropping old indexes...", end=' ', flush=True)
        cur.execute("DROP INDEX IF EXISTS idx_title_trgm")
        cur.execute("DROP INDEX IF EXISTS idx_desc_trgm")
        print("✓")
        
        print("  Creating title index...", end=' ', flush=True)
        cur.execute("CREATE INDEX idx_title_trgm ON worlds USING gin (title gin_trgm_ops)")
        print("✓")
        
        print("  Creating description index...", end=' ', flush=True)
        cur.execute("CREATE INDEX idx_desc_trgm ON worlds USING gin (description gin_trgm_ops)")
        print("✓")
        
        conn.commit()
        print("\n✓ Indexes created successfully")
        
        cur.close()
        conn.close()
        
        print("\n" + "="*60)
        print("🎉 DATABASE SEEDING COMPLETED!")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='pg_trgm Fuzzy Search Demo - Data Seeding Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # 抓取 10,000 筆資料 (預設，並行模式)
  python seed.py
  
  # 使用非並行模式（依序抓取，較慢但更穩定）
  python seed.py --no-parallel
  
  # 抓取 1,000 筆資料（並行模式）
  python seed.py --total 1000
  
  # 抓取 1,000 筆資料（非並行模式）
  python seed.py --total 1000 --no-parallel
  
  # 自訂各來源數量（並行模式）
  python seed.py --arxiv 2500 --wikipedia 2500 --books 2000 \\
                 --quotable 1500 --facts 1000 --zenquotes 500
  
  # 自訂各來源數量（非並行模式）
  python seed.py --arxiv 2500 --wikipedia 2500 --books 2000 \\
                 --quotable 1500 --facts 1000 --zenquotes 500 --no-parallel
  
  # 只抓取名言和冷知識（非並行模式，適合除錯）
  python seed.py --quotable 500 --facts 500 --zenquotes 100 \\
                 --arxiv 0 --wikipedia 0 --books 0 --no-parallel
  
  # 快速測試 (100 筆，自動分配)
  python seed.py --total 100
  
  # 跳過 Wikipedia 暢銷書
  python seed.py --skip-wiki-bestsellers
        '''
    )
    
    parser.add_argument(
        '--total', 
        type=int, 
        default=10000,
        help='總資料筆數目標 (預設: 10000)。會自動分配給各來源'
    )
    
    parser.add_argument(
        '--arxiv',
        type=int,
        help='ArXiv 論文數量 (學術摘要)'
    )
    
    parser.add_argument(
        '--wikipedia',
        type=int,
        help='Wikipedia 條目數量 (百科全書)'
    )
    
    parser.add_argument(
        '--books',
        type=int,
        help='Google Books 數量 (書籍簡介)'
    )
    
    parser.add_argument(
        '--quotable',
        type=int,
        help='Quotable.io 名言數量 (勵志名言)'
    )
    
    parser.add_argument(
        '--facts',
        type=int,
        help='UselessFacts 冷知識數量 (有趣事實)'
    )
    
    parser.add_argument(
        '--zenquotes',
        type=int,
        help='ZenQuotes 名言數量 (額外名言來源)'
    )
    
    parser.add_argument(
        '--skip-wiki-bestsellers',
        action='store_true',
        help='跳過 Wikipedia 暢銷書清單 (約 50 筆)'
    )
    
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='停用並行模式，依序抓取各來源（較慢但更穩定）'
    )
    
    args = parser.parse_args()
    
    # 如果使用者指定了個別來源數量，則使用指定值
    if (args.arxiv is not None or args.wikipedia is not None or args.books is not None or
        args.quotable is not None or args.facts is not None or args.zenquotes is not None):
        arxiv_count = args.arxiv if args.arxiv is not None else 0
        wiki_count = args.wikipedia if args.wikipedia is not None else 0
        books_count = args.books if args.books is not None else 0
        quotable_count = args.quotable if args.quotable is not None else 0
        facts_count = args.facts if args.facts is not None else 0
        zenquotes_count = args.zenquotes if args.zenquotes is not None else 0
    else:
        # 否則根據 total 自動分配
        # 25% ArXiv, 25% Wikipedia, 20% Books, 15% Quotable, 10% Facts, 5% ZenQuotes
        arxiv_count = int(args.total * 0.25)
        wiki_count = int(args.total * 0.25)
        books_count = int(args.total * 0.20)
        quotable_count = int(args.total * 0.15)
        facts_count = int(args.total * 0.10)
        zenquotes_count = int(args.total * 0.05)
    
    return {
        'arxiv': arxiv_count,
        'wikipedia': wiki_count,
        'books': books_count,
        'quotable': quotable_count,
        'facts': facts_count,
        'zenquotes': zenquotes_count,
        'skip_bestsellers': args.skip_wiki_bestsellers,
        'parallel': not args.no_parallel,
        'total_target': args.total
    }

def main():
    # Parse command line arguments
    config = parse_arguments()
    
    # Record total start time
    total_start_time = time.time()
    
    print("=" * 60)
    print("pg_trgm Fuzzy Search Demo - Data Seeding")
    print("=" * 60)
    print(f"Target Configuration:")
    print(f"  ArXiv Papers: {config['arxiv']}")
    print(f"  Wikipedia Articles: {config['wikipedia']}")
    print(f"  Google Books: {config['books']}")
    print(f"  Quotable Quotes: {config['quotable']}")
    print(f"  Random Facts: {config['facts']}")
    print(f"  ZenQuotes: {config['zenquotes']}")
    print(f"  Wikipedia Bestsellers: {'No' if config['skip_bestsellers'] else 'Yes (~50)'}")
    print(f"  Execution Mode: {'PARALLEL' if config['parallel'] else 'SEQUENTIAL'}")
    print(f"  Total Target: ~{config['total_target']}")
    print("=" * 60)
    
    if config['parallel']:
        print("\n🚀 PARALLEL MODE: All sources fetching simultaneously!\n")
    else:
        print("\n⏳ SEQUENTIAL MODE: Fetching sources one by one...\n")
    
    all_data = []
    arxiv_papers = []
    wiki_articles = []
    google_books = []
    quotable_quotes = []
    random_facts = []
    zen_quotes = []
    wiki_books = []
    
    if config['parallel']:
        # ========== 並行模式 ==========
        # Use ThreadPoolExecutor to fetch from all sources in parallel
        # Increased max_workers to 7 to handle all sources simultaneously
        with ThreadPoolExecutor(max_workers=7) as executor:
            futures = {}
            
            # Submit tasks for each data source
            if config['arxiv'] > 0:
                futures['arxiv'] = executor.submit(scrape_arxiv_papers, config['arxiv'])
            
            if config['wikipedia'] > 0:
                futures['wikipedia'] = executor.submit(scrape_wikipedia_bulk, config['wikipedia'])
            
            if config['books'] > 0:
                futures['google_books'] = executor.submit(scrape_google_books_free, config['books'])
            
            if config['quotable'] > 0:
                futures['quotable'] = executor.submit(scrape_quotable_quotes, config['quotable'])
            
            if config['facts'] > 0:
                futures['facts'] = executor.submit(scrape_random_facts, config['facts'])
            
            if config['zenquotes'] > 0:
                futures['zenquotes'] = executor.submit(scrape_zenquotes, config['zenquotes'])
            
            if not config['skip_bestsellers']:
                futures['wiki_books'] = executor.submit(scrape_wikipedia_books)
            
            # Collect results as they complete
            for source, future in futures.items():
                try:
                    result = future.result()
                    if source == 'arxiv':
                        arxiv_papers = result
                    elif source == 'wikipedia':
                        wiki_articles = result
                    elif source == 'google_books':
                        google_books = result
                    elif source == 'quotable':
                        quotable_quotes = result
                    elif source == 'facts':
                        random_facts = result
                    elif source == 'zenquotes':
                        zen_quotes = result
                    elif source == 'wiki_books':
                        wiki_books = result
                except Exception as e:
                    print(f"\n✗ Error fetching {source}: {e}")
    
    else:
        # ========== 非並行模式（依序執行）==========
        try:
            if config['arxiv'] > 0:
                arxiv_papers = scrape_arxiv_papers(config['arxiv'])
            
            if config['wikipedia'] > 0:
                wiki_articles = scrape_wikipedia_bulk(config['wikipedia'])
            
            if config['books'] > 0:
                google_books = scrape_google_books_free(config['books'])
            
            if config['quotable'] > 0:
                quotable_quotes = scrape_quotable_quotes(config['quotable'])
            
            if config['facts'] > 0:
                random_facts = scrape_random_facts(config['facts'])
            
            if config['zenquotes'] > 0:
                zen_quotes = scrape_zenquotes(config['zenquotes'])
            
            if not config['skip_bestsellers']:
                wiki_books = scrape_wikipedia_books()
                
        except Exception as e:
            print(f"\n✗ Error during sequential fetching: {e}")
    
    # Combine all results
    all_data.extend(arxiv_papers)
    all_data.extend(wiki_articles)
    all_data.extend(google_books)
    all_data.extend(quotable_quotes)
    all_data.extend(random_facts)
    all_data.extend(zen_quotes)
    all_data.extend(wiki_books)
    
    # Calculate total data collection time
    data_collection_time = time.time() - total_start_time
    
    print(f"\n{'='*60}")
    print(f"Data Collection Summary:")
    print(f"  ArXiv Papers: {len(arxiv_papers)}")
    print(f"  Wikipedia Articles: {len(wiki_articles)}")
    print(f"  Google Books: {len(google_books)}")
    print(f"  Quotable Quotes: {len(quotable_quotes)}")
    print(f"  Random Facts: {len(random_facts)}")
    print(f"  ZenQuotes: {len(zen_quotes)}")
    print(f"  Wikipedia Books: {len(wiki_books)}")
    print(f"  Total collected: {len(all_data)}")
    print(f"  ⏱️  Total data collection time: {data_collection_time:.2f} seconds ({data_collection_time/60:.2f} minutes)")
    print(f"{'='*60}\n")
    
    # Remove duplicates based on title (case-insensitive)
    seen = set()
    unique_books = []
    for title, desc in all_data:
        title_lower = title.lower()
        if title_lower not in seen and desc:  # Ensure description exists
            seen.add(title_lower)
            unique_books.append((title, desc))
    
    print(f"Total unique entries after deduplication: {len(unique_books)}")
    
    if len(unique_books) < 10:
        print("Warning: Less than 10 entries scraped. Please check your internet connection.")
        return
    
    # Setup database
    create_database_if_not_exists()
    
    # Insert into database
    insert_books_to_db(unique_books)

if __name__ == "__main__":
    main()
