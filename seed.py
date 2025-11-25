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

# Database connection parameters
DB_PARAMS = {
    'host': 'localhost',
    'port': 5432,
    'database': 'testdb',
    'user': 'postgres',
    'password': 'password'
}

def scrape_wikipedia_books():
    """Scrape best-selling books from Wikipedia"""
    print("Scraping Wikipedia best-selling books...")
    url = "https://en.wikipedia.org/wiki/List_of_best-selling_books"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        books = []
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
                        # Try to get description from book's Wikipedia page
                        description = get_book_description(link.get('href'))
                        books.append((title, description))
                        print(f"  Found: {title}")
                        time.sleep(0.3)  # Be polite to Wikipedia
                
                if len(books) >= 50:
                    break
            
            if len(books) >= 50:
                break
        
        print(f"Scraped {len(books)} books from Wikipedia")
        return books
    
    except Exception as e:
        print(f"Error scraping Wikipedia: {e}")
        return []

def get_book_description(wiki_path):
    """Get book description from its Wikipedia page"""
    if not wiki_path or wiki_path.startswith('http'):
        return ""
    
    try:
        url = f"https://en.wikipedia.org{wiki_path}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find first paragraph with actual content
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if content_div:
            paragraphs = content_div.find_all('p', recursive=False)
            for p in paragraphs:
                text = p.get_text(strip=True)
                # Skip short paragraphs (likely navigation or notes)
                if len(text) > 100:
                    # Clean up citations and extra whitespace
                    text = re.sub(r'\[.*?\]', '', text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    return text[:500]  # Limit description length
        
        return ""
    
    except Exception as e:
        print(f"    Error getting description: {e}")
        return ""

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

def insert_books_to_db(books):
    """Insert books into PostgreSQL database"""
    print("\nConnecting to database...")
    
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        print("Clearing existing data...")
        cur.execute("DELETE FROM worlds")
        
        print(f"Inserting {len(books)} books...")
        for title, description in books:
            cur.execute(
                "INSERT INTO worlds (title, description) VALUES (%s, %s)",
                (title, description)
            )
        
        conn.commit()
        
        # Get count
        cur.execute("SELECT COUNT(*) FROM worlds")
        count = cur.fetchone()[0]
        print(f"Successfully inserted {count} records")
        
        # Create trigram indexes
        print("\nCreating trigram indexes...")
        cur.execute("DROP INDEX IF EXISTS idx_title_trgm")
        cur.execute("DROP INDEX IF EXISTS idx_desc_trgm")
        
        cur.execute("CREATE INDEX idx_title_trgm ON worlds USING gin (title gin_trgm_ops)")
        cur.execute("CREATE INDEX idx_desc_trgm ON worlds USING gin (description gin_trgm_ops)")
        
        conn.commit()
        print("Indexes created successfully")
        
        cur.close()
        conn.close()
        print("\nDatabase seeding completed!")
        
    except Exception as e:
        print(f"Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

def main():
    print("=" * 60)
    print("pg_trgm Fuzzy Search Demo - Data Seeding")
    print("=" * 60)
    
    # Scrape data from multiple sources
    wiki_books = scrape_wikipedia_books()
    openlibrary_books = scrape_openlibrary_books()
    
    # Combine and deduplicate
    all_books = wiki_books + openlibrary_books
    
    # Remove duplicates based on title (case-insensitive)
    seen = set()
    unique_books = []
    for title, desc in all_books:
        title_lower = title.lower()
        if title_lower not in seen:
            seen.add(title_lower)
            unique_books.append((title, desc))
    
    print(f"\nTotal unique books: {len(unique_books)}")
    
    if len(unique_books) < 10:
        print("Warning: Less than 10 books scraped. Please check your internet connection.")
        return
    
    # Insert into database
    insert_books_to_db(unique_books)

if __name__ == "__main__":
    main()
