import arxiv
import requests
import json
import datetime
import time
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import re

# --- Configuration ---
# IMPORTANT: For IEEE, ACM, and Springer, direct scraping can be unreliable,
# subject to rate limits, and against terms of service.
# Official APIs often require API keys/subscriptions.
# This script uses basic scraping for demonstration, which might break.
# For production use, consider official APIs or commercial aggregators.

# --- Constants ---
ARXIV_URL = "https://arxiv.org/"
IEEE_SEARCH_URL = "https://ieeexplore.ieee.org/search/searchresults.jsp"
ACM_SEARCH_URL = "https://dl.acm.org/search/2.4/results.cfm" # Note: ACM's search is complex, this is a simplified approach
SPRINGER_SEARCH_URL = "https://link.springer.com/search"

# --- Helper Functions ---
def construct_arxiv_query(keywords: List[str]) -> str:
    """Constructs a search query string for the arXiv API."""
    # Example: 'cat:cs.CL AND abs:"natural language processing"'
    # For general keywords, we search in the abstract.
    formatted_keywords = [f'abs:"{k}"' for k in keywords]
    return " AND ".join(formatted_keywords)

def fetch_arxiv_papers(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Fetches papers from arXiv based on the search query."""
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )
    results = client.results(search)
    papers = []
    for result in results:
        papers.append({
            "id": result.entry_id.split("arxiv.org/abs/")[-1],
            "title": result.title,
            "summary": result.summary,
            "published": result.published.strftime("%Y-%m-%d"),
            "url": result.entry_id,
            "authors": [author.name for author in result.authors],
            "source": "arXiv"
        })
    return papers

def fetch_ieee_papers(keywords: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Fetches papers from IEEE Xplore.
    Note: This uses basic scraping and might be unstable or blocked.
    For robust access, an IEEE API key is recommended.
    """
    search_term = " ".join(keywords)
    params = {
        "queryText": search_term,
        "rowsPerPage": max_results,
        "highlight": "true",
        "returnType": "SEARCH"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    papers = []
    try:
        response = requests.get(IEEE_SEARCH_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # IEEE's HTML structure can change. This is a best-effort attempt.
        # Look for search results, typically in a list or grid.
        # This example looks for common patterns, adjust as needed.
        for item in soup.find_all('div', class_='List-results-items'): # Common class for results
            title_tag = item.find('h2', class_='document-title')
            link_tag = item.find('a', href=True)
            abstract_tag = item.find('div', class_='description')
            date_tag = item.find('div', class_='publication-year') # Or similar

            if title_tag and link_tag:
                title = title_tag.get_text(strip=True)
                url = "https://ieeexplore.ieee.org" + link_tag['href']
                summary = abstract_tag.get_text(strip=True) if abstract_tag else "N/A"
                published = date_tag.get_text(strip=True) if date_tag else "N/A"
                papers.append({
                    "id": url.split('/')[-1],
                    "title": title,
                    "summary": summary,
                    "published": published,
                    "url": url,
                    "authors": [], # Hard to parse reliably without more specific selectors
                    "source": "IEEE Xplore"
                })
                if len(papers) >= max_results:
                    break
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from IEEE Xplore: {e}")
    except Exception as e:
        print(f"Error parsing IEEE Xplore results: {e}")
    return papers

def fetch_acm_papers(keywords: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Fetches papers from ACM Digital Library.
    Note: This uses basic scraping and might be unstable or blocked.
    ACM's search interface is complex; this is a simplified approach.
    """
    search_term = " ".join(keywords)
    params = {
        "query": search_term,
        "start": 0, # Start index for results
        "pageSize": max_results
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    papers = []
    try:
        response = requests.get(ACM_SEARCH_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # ACM's HTML structure is also dynamic. This is a best-effort.
        for item in soup.find_all('div', class_='issue-item'): # Common class for results
            title_tag = item.find('a', class_='issue-item__title')
            link_tag = title_tag # The title itself is the link
            authors_tag = item.find('div', class_='issue-item__authors')
            date_tag = item.find('span', class_='issue-item__date')

            if title_tag and link_tag:
                title = title_tag.get_text(strip=True)
                url = "https://dl.acm.org" + link_tag['href']
                authors = [a.get_text(strip=True) for a in authors_tag.find_all('a')] if authors_tag else []
                published = date_tag.get_text(strip=True) if date_tag else "N/A"
                papers.append({
                    "id": url.split('/')[-1],
                    "title": title,
                    "summary": "N/A", # ACM often requires clicking through for abstract
                    "published": published,
                    "url": url,
                    "authors": authors,
                    "source": "ACM Digital Library"
                })
                if len(papers) >= max_results:
                    break
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from ACM Digital Library: {e}")
    except Exception as e:
        print(f"Error parsing ACM Digital Library results: {e}")
    return papers

def fetch_springer_papers(keywords: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Fetches papers from SpringerLink.
    Note: This uses basic scraping and might be unstable or blocked.
    """
    search_term = " ".join(keywords)
    params = {
        "query": search_term,
        "facet-start-year": datetime.date.today().year - 5, # Limit to recent years
        "facet-end-year": datetime.date.today().year,
        "page": 1,
        "per_page": max_results
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    papers = []
    try:
        response = requests.get(SPRINGER_SEARCH_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        for item in soup.find_all('li', class_='c-results-list__item'):
            title_tag = item.find('a', class_='c-card__link')
            link_tag = title_tag
            authors_tag = item.find('span', class_='c-author-list')
            date_tag = item.find('time')

            if title_tag and link_tag:
                title = title_tag.get_text(strip=True)
                url = "https://link.springer.com" + link_tag['href']
                authors = [a.get_text(strip=True) for a in authors_tag.find_all('a')] if authors_tag else []
                published = date_tag['datetime'] if date_tag and 'datetime' in date_tag.attrs else "N/A"
                papers.append({
                    "id": url.split('/')[-1],
                    "title": title,
                    "summary": "N/A", # Springer often requires clicking through for abstract
                    "published": published,
                    "url": url,
                    "authors": authors,
                    "source": "SpringerLink"
                })
                if len(papers) >= max_results:
                    break
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from SpringerLink: {e}")
    except Exception as e:
        print(f"Error parsing SpringerLink results: {e}")
    return papers

def get_papers_for_keywords(
    keyword_sets: List[List[str]], max_results_per_source: int = 5
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetches papers for each keyword set from all specified sources.
    """
    all_results: Dict[str, List[Dict[str, Any]]] = {}
    for keywords in keyword_sets:
        keyword_str = " ".join(keywords)
        print(f"Fetching papers for: {keyword_str}")
        combined_papers = []

        # Fetch from arXiv
        arxiv_query = construct_arxiv_query(keywords)
        arxiv_papers = fetch_arxiv_papers(arxiv_query, max_results_per_source)
        combined_papers.extend(arxiv_papers)
        print(f"  Found {len(arxiv_papers)} papers from arXiv.")
        time.sleep(0.5) # Be polite to APIs

        # Fetch from IEEE Xplore (Scraping - prone to issues)
        ieee_papers = fetch_ieee_papers(keywords, max_results_per_source)
        combined_papers.extend(ieee_papers)
        print(f"  Found {len(ieee_papers)} papers from IEEE Xplore.")
        time.sleep(1) # Be polite to websites

        # Fetch from ACM Digital Library (Scraping - prone to issues)
        acm_papers = fetch_acm_papers(keywords, max_results_per_source)
        combined_papers.extend(acm_papers)
        print(f"  Found {len(acm_papers)} papers from ACM Digital Library.")
        time.sleep(1) # Be polite to websites

        # Fetch from SpringerLink (Scraping - prone to issues)
        springer_papers = fetch_springer_papers(keywords, max_results_per_source)
        combined_papers.extend(springer_papers)
        print(f"  Found {len(springer_papers)} papers from SpringerLink.")
        time.sleep(1) # Be polite to websites

        # Sort combined papers by published date (most recent first)
        combined_papers.sort(
            key=lambda x: datetime.datetime.strptime(x.get("published", "1900-01-01").split('T')[0], "%Y-%m-%d")
            if x.get("published") and re.match(r'\d{4}-\d{2}-\d{2}', x["published"].split('T')[0])
            else datetime.datetime(1900, 1, 1),
            reverse=True
        )
        all_results[keyword_str] = combined_papers
    return all_results

def write_markdown(
    data: Dict[str, List[Dict[str, Any]]], md_filename: str, maximum_papers_per_category: int = 20
) -> None:
    """Writes the fetched paper data to a markdown file."""
    date_now = datetime.date.today().strftime("%Y.%m.%d")

    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(f"# Research Paper Digest - {date_now}\n\n")
        f.write("This document summarizes recent research papers based on your specified keywords.\n\n")
        f.write("<details>\n")
        f.write("  <summary>Table of Contents</summary>\n")
        f.write("  <ol>\n")
        for keyword_str in data.keys():
            if data[keyword_str]:
                kw_id = keyword_str.replace(" ", "-").lower()
                f.write(f"    <li><a href=\"#{kw_id}\">{keyword_str}</a></li>\n")
        f.write("  </ol>\n")
        f.write("</details>\n\n")

        for keyword_str, papers in data.items():
            if not papers:
                continue

            kw_id = keyword_str.replace(" ", "-").lower()
            f.write(f'<h2 id="{kw_id}"> {keyword_str} </h2>\n\n')
            f.write("| Title | Authors | Source | Published | Link |\n")
            f.write("| --- | --- | --- | --- | --- |\n")
            for idx, paper_info in enumerate(papers):
                if idx >= maximum_papers_per_category:
                    break
                title = paper_info["title"].replace("\n", " ").strip()
                authors = ", ".join(paper_info.get("authors", ["N/A"]))
                source = paper_info["source"]
                published = paper_info["published"]
                url = paper_info["url"]
                f.write(f"| {title} | {authors} | {source} | {published} | [Link]({url}) |\n")
            f.write("\n")

def main() -> None:
    """Main function to orchestrate paper fetching and markdown generation."""
    max_results_per_source = 5  # Max papers to fetch per source per keyword set
    max_display_per_category = 10 # Max papers to display in markdown per keyword set
    md_file = "research_papers_digest.md"
    config_file = "config/keywords.json"

    try:
        with open(config_file, "r", encoding="utf-8") as file:
            config_data = json.load(file)
            keyword_sets = config_data.get("keyword_sets", [])
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file}' not found.")
        print("Please create a 'config' directory and a 'keywords.json' file inside it.")
        print("Example keywords.json: {\"keyword_sets\": [[\"5G\", \"network slicing\"], [\"AI\", \"edge computing\"] ]}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not parse '{config_file}'. Ensure it's valid JSON.")
        return

    if not keyword_sets:
        print("No keyword sets found in the configuration file. Exiting.")
        return

    print("Starting paper fetching...")
    all_fetched_papers = get_papers_for_keywords(keyword_sets, max_results_per_source)

    if not any(all_fetched_papers.values()):
        print("No papers were fetched for any keyword set.")
        return

    print(f"\nWriting results to {md_file}...")
    write_markdown(all_fetched_papers, md_file, max_display_per_category)
    print("Script finished successfully!")

if __name__ == "__main__":
    main()
