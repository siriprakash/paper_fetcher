import arxiv
import requests
import json
import datetime
import time
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import re

ARXIV_URL = "https://arxiv.org/"

def construct_arxiv_query(keywords: List[str]) -> str:
    formatted_keywords = [f'abs:"{k}"' for k in keywords]
    return " AND ".join(formatted_keywords)

def fetch_arxiv_papers(query: str, max_results: int = 300) -> List[Dict[str, Any]]:
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


def get_papers_for_keywords(
    keyword_sets: List[List[str]], max_results_per_source: int = 300
) -> Dict[str, List[Dict[str, Any]]]:
    all_results: Dict[str, List[Dict[str, Any]]] = {}
    for keywords in keyword_sets:
        keyword_str = " ".join(keywords)
        print(f"Fetching papers for: {keyword_str}")
        combined_papers = []

        arxiv_query = construct_arxiv_query(keywords)
        arxiv_papers = fetch_arxiv_papers(arxiv_query, max_results_per_source)
        combined_papers.extend(arxiv_papers)
        print(f"  Found {len(arxiv_papers)} papers from arXiv.")
        time.sleep(0.5) # Be polite to APIs

        combined_papers.sort(
            key=lambda x: datetime.datetime.strptime(x.get("published", "1900-01-01").split('T')[0], "%Y-%m-%d")
            if x.get("published") and re.match(r'\d{4}-\d{2}-\d{2}', x["published"].split('T')[0])
            else datetime.datetime(1900, 1, 1),
            reverse=True
        )
        all_results[keyword_str] = combined_papers
    return all_results

def write_markdown(
    data: Dict[str, List[Dict[str, Any]]], md_filename: str, maximum_papers_per_category: int = 300
) -> None:

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
    max_results_per_source = 300  # Max papers to fetch per source per keyword set
    max_display_per_category = 300 # Max papers to display in markdown per keyword set
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
