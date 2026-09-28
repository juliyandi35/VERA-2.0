"""
academic_crawler.py
Multi-Source Academic Paper Crawler for V.E.R.A. 2.0
Supports 7 Academic Repositories & Registries:
1. arXiv (Physics, Computer Science, AI, Mathematics)
2. OpenAlex (250M+ interdisciplinary scientific works)
3. Crossref (150M+ peer-reviewed publisher DOI registry)
4. PubMed & PubMed Central / PMC (36M+ biomedical & clinical research)
5. Unpaywall (Automated legal Open Access PDF resolution from DOI)
6. Europe PMC (40M+ life sciences & molecular biology articles)
7. bioRxiv & medRxiv (Preprints in biology and health sciences)
"""

import os
import re
import time
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

USER_AGENT = "VERAResearchAssistant/2.0 (mailto:juliyandi35@gmail.com; educational research bot)"
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/html, application/pdf"
}

def sanitize_filename(filename: str) -> str:
    """Sanitize string for safe file names."""
    clean = re.sub(r'[\\/*?:"<>|]', "", filename)
    clean = re.sub(r'\s+', "_", clean.strip())
    return clean[:120] if len(clean) > 120 else clean

def decode_openalex_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
    """Reconstruct abstract from OpenAlex inverted index structure."""
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)

def resolve_unpaywall_pdf(doi: str, email: str = "juliyandi35@gmail.com") -> Optional[str]:
    """Resolve legal Open Access PDF URL using Unpaywall API from DOI."""
    if not doi:
        return None
    clean_doi = doi.replace("https://doi.org/", "").strip()
    try:
        url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(clean_doi)}?email={email}"
        res = requests.get(url, headers=DEFAULT_HEADERS, timeout=7)
        if res.status_code == 200:
            data = res.json()
            best_oa = data.get("best_oa_location") or {}
            pdf_url = best_oa.get("url_for_pdf") or best_oa.get("url")
            if pdf_url:
                return pdf_url
    except Exception:
        pass
    return None

def download_pdf_file(pdf_url: str, output_path: str) -> bool:
    """Download PDF file safely and verify that the file starts with %PDF."""
    if not pdf_url:
        return False
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/pdf,application/octet-stream,*/*"
        }
        res = requests.get(pdf_url, headers=headers, stream=True, timeout=25, allow_redirects=True)
        if res.status_code != 200:
            return False
        
        # Check first chunk
        first_chunk = next(res.iter_content(chunk_size=1024), b"")
        if not first_chunk or (b"%PDF" not in first_chunk[:50] and b"PDF" not in first_chunk[:100]):
            # Some servers require different content negotiation or redirect
            return False
            
        with open(output_path, "wb") as f:
            f.write(first_chunk)
            for chunk in res.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception:
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass
        return False

# ==========================================
# 1. arXiv Crawler
# ==========================================
def crawl_arxiv(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    papers = []
    try:
        import arxiv
        client = arxiv.Client(page_size=max_results, delay_seconds=1.0)
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        for p in client.results(search):
            papers.append({
                "source": "arXiv",
                "title": p.title.replace("\n", " ").strip(),
                "authors": [a.name for a in p.authors],
                "year": p.published.year if p.published else "N/A",
                "abstract": p.summary.replace("\n", " ").strip(),
                "doi": p.doi or "",
                "url": p.entry_id,
                "pdf_url": p.pdf_url,
                "journal": "arXiv preprint " + (p.primary_category or ""),
                "id": p.get_short_id()
            })
    except Exception as e:
        print(f"[arXiv error]: {e}")
    return papers

# ==========================================
# 2. OpenAlex Crawler (250M+ Works)
# ==========================================
def crawl_openalex(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    papers = []
    try:
        url = f"https://api.openalex.org/works?search={urllib.parse.quote(query)}&per-page={max_results}"
        res = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for item in data.get("results", []):
                title = item.get("title") or "Untitled Work"
                authorships = item.get("authorships") or []
                authors = [a.get("author", {}).get("display_name", "") for a in authorships if a.get("author")]
                year = item.get("publication_year") or "N/A"
                abstract = decode_openalex_abstract(item.get("abstract_inverted_index"))
                doi = item.get("doi") or ""
                
                # Check direct open access PDF URL
                oa_info = item.get("open_access") or {}
                best_loc = item.get("best_oa_location") or item.get("primary_location") or {}
                pdf_url = oa_info.get("oa_url") or best_loc.get("pdf_url")
                
                # Venue/Journal
                source_info = best_loc.get("source") or {}
                journal = source_info.get("display_name") or "Academic Publication"
                
                papers.append({
                    "source": "OpenAlex",
                    "title": title.replace("\n", " ").strip(),
                    "authors": authors,
                    "year": year,
                    "abstract": abstract,
                    "doi": doi,
                    "url": doi or item.get("id") or "",
                    "pdf_url": pdf_url,
                    "journal": journal,
                    "id": item.get("id", "").replace("https://openalex.org/", "")
                })
    except Exception as e:
        print(f"[OpenAlex error]: {e}")
    return papers

# ==========================================
# 3. Crossref Crawler (150M+ Works)
# ==========================================
def crawl_crossref(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    papers = []
    try:
        url = f"https://api.crossref.org/works?query={urllib.parse.quote(query)}&rows={max_results}"
        res = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        if res.status_code == 200:
            items = res.json().get("message", {}).get("items", [])
            for item in items:
                title_list = item.get("title") or []
                title = title_list[0] if title_list else "Untitled"
                
                authors = []
                for a in item.get("author", []):
                    name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                    if name:
                        authors.append(name)
                
                published = item.get("published") or item.get("issued") or {}
                date_parts = published.get("date-parts", [[None]])
                year = date_parts[0][0] if date_parts and date_parts[0] else "N/A"
                
                abstract = item.get("abstract", "")
                if abstract:
                    abstract = re.sub(r'<[^>]+>', '', abstract).strip()
                
                doi = item.get("DOI") or ""
                doi_url = f"https://doi.org/{doi}" if doi else ""
                
                # PDF links from Crossref metadata
                pdf_url = None
                for link in item.get("link", []):
                    if "pdf" in link.get("content-type", "").lower():
                        pdf_url = link.get("URL")
                        break
                        
                container = item.get("container-title") or []
                journal = container[0] if container else "Scholarly Journal"
                
                papers.append({
                    "source": "Crossref",
                    "title": title.replace("\n", " ").strip(),
                    "authors": authors,
                    "year": year,
                    "abstract": abstract,
                    "doi": doi_url,
                    "url": doi_url or item.get("URL") or "",
                    "pdf_url": pdf_url,
                    "journal": journal,
                    "id": doi
                })
    except Exception as e:
        print(f"[Crossref error]: {e}")
    return papers

# ==========================================
# 4. PubMed & PMC Crawler (36M+ Works)
# ==========================================
def crawl_pubmed_pmc(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    papers = []
    try:
        # Step 1: Search PMC for full-text open access articles
        pmc_search = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc&term={urllib.parse.quote(query)}+AND+open_access[filter]&retmode=json&retmax={max_results}"
        res = requests.get(pmc_search, headers=DEFAULT_HEADERS, timeout=8)
        pmc_ids = []
        if res.status_code == 200:
            pmc_ids = res.json().get("esearchresult", {}).get("idlist", [])
            
        # Fallback to PubMed if PMC yielded few results
        pubmed_ids = []
        if len(pmc_ids) < max_results:
            pubmed_search = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(query)}&retmode=json&retmax={max_results}"
            p_res = requests.get(pubmed_search, headers=DEFAULT_HEADERS, timeout=8)
            if p_res.status_code == 200:
                pubmed_ids = p_res.json().get("esearchresult", {}).get("idlist", [])

        # Fetch details for PMC articles
        for pmcid in pmc_ids[:max_results]:
            sum_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pmc&id={pmcid}&retmode=json"
            s_res = requests.get(sum_url, headers=DEFAULT_HEADERS, timeout=6)
            if s_res.status_code == 200:
                doc = s_res.json().get("result", {}).get(pmcid, {})
                title = doc.get("title") or "Untitled PMC Paper"
                authors = [a.get("name", "") for a in doc.get("authors", []) if a.get("name")]
                year = doc.get("pubdate", "")[:4] or "N/A"
                doi = ""
                for aid in doc.get("articleids", []):
                    if aid.get("idtype") == "doi":
                        doi = f"https://doi.org/{aid.get('value')}"
                
                # NCBI PMC direct PDF link format
                pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/pdf/"
                
                papers.append({
                    "source": "PubMed/PMC",
                    "title": title.replace("\n", " ").strip(),
                    "authors": authors,
                    "year": year,
                    "abstract": f"Biomedical research article indexed in PubMed Central (PMC{pmcid}).",
                    "doi": doi,
                    "url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/",
                    "pdf_url": pdf_url,
                    "journal": doc.get("source") or "PMC Biomedical Journal",
                    "id": f"PMC{pmcid}"
                })

        # Fetch details for PubMed articles if needed
        needed = max_results - len(papers)
        if needed > 0 and pubmed_ids:
            for pmid in pubmed_ids[:needed]:
                sum_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmmid}&retmode=json"
                s_res = requests.get(sum_url, headers=DEFAULT_HEADERS, timeout=6)
                if s_res.status_code == 200:
                    doc = s_res.json().get("result", {}).get(pmid, {})
                    title = doc.get("title") or "Untitled PubMed Paper"
                    authors = [a.get("name", "") for a in doc.get("authors", []) if a.get("name")]
                    year = doc.get("pubdate", "")[:4] or "N/A"
                    doi = ""
                    for aid in doc.get("articleids", []):
                        if aid.get("idtype") == "doi":
                            doi = f"https://doi.org/{aid.get('value')}"
                    
                    papers.append({
                        "source": "PubMed",
                        "title": title.replace("\n", " ").strip(),
                        "authors": authors,
                        "year": year,
                        "abstract": f"PubMed indexed clinical study (PMID: {pmid}).",
                        "doi": doi,
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        "pdf_url": None, # Will be resolved by Unpaywall
                        "journal": doc.get("source") or "PubMed Journal",
                        "id": f"PMID{pmid}"
                    })
    except Exception as e:
        print(f"[PubMed/PMC error]: {e}")
    return papers

# ==========================================
# 5. Europe PMC Crawler (40M+ Works)
# ==========================================
def crawl_europe_pmc(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    papers = []
    try:
        url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={urllib.parse.quote(query)}&format=json&resultType=core&pageSize={max_results}"
        res = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        if res.status_code == 200:
            results = res.json().get("resultList", {}).get("result", [])
            for item in results:
                title = item.get("title") or "Untitled Europe PMC Paper"
                author_str = item.get("authorString", "")
                authors = [a.strip() for a in author_str.split(",") if a.strip()]
                year = item.get("pubYear") or "N/A"
                abstract = item.get("abstractText") or ""
                doi = f"https://doi.org/{item.get('doi')}" if item.get("doi") else ""
                
                # Check PDF URL
                pdf_url = None
                pmcid = item.get("pmcid")
                if pmcid:
                    pdf_url = f"https://europepmc.org/articles/{pmcid}?pdf=render"
                else:
                    for link in item.get("fullTextUrlList", {}).get("fullTextUrl", []):
                        if link.get("documentStyle") == "pdf":
                            pdf_url = link.get("url")
                            break

                papers.append({
                    "source": "Europe PMC",
                    "title": title.replace("\n", " ").strip(),
                    "authors": authors,
                    "year": year,
                    "abstract": abstract,
                    "doi": doi,
                    "url": f"https://europepmc.org/article/MED/{item.get('id')}",
                    "pdf_url": pdf_url,
                    "journal": item.get("journalTitle") or "Europe PMC Journal",
                    "id": item.get("id") or item.get("pmcid") or ""
                })
    except Exception as e:
        print(f"[Europe PMC error]: {e}")
    return papers

# ==========================================
# 6. bioRxiv & medRxiv Crawler
# ==========================================
def crawl_biorxiv_medrxiv(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    papers = []
    try:
        # Query Crossref targeted to Cold Spring Harbor Laboratory (publisher of bioRxiv and medRxiv)
        search_query = f"{query} biorxiv medrxiv"
        url = f"https://api.crossref.org/works?query={urllib.parse.quote(search_query)}&filter=prefix:10.1101&rows={max_results}"
        res = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        if res.status_code == 200:
            items = res.json().get("message", {}).get("items", [])
            for item in items:
                title_list = item.get("title") or []
                title = title_list[0] if title_list else "Untitled Preprint"
                
                authors = []
                for a in item.get("author", []):
                    name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                    if name:
                        authors.append(name)
                        
                published = item.get("published") or item.get("issued") or {}
                date_parts = published.get("date-parts", [[None]])
                year = date_parts[0][0] if date_parts and date_parts[0] else "N/A"
                
                doi = item.get("DOI") or ""
                doi_url = f"https://doi.org/{doi}" if doi else ""
                
                # bioRxiv standard PDF URL pattern
                pdf_url = f"https://www.biorxiv.org/content/{doi}.full.pdf" if doi else None
                
                papers.append({
                    "source": "bioRxiv/medRxiv",
                    "title": title.replace("\n", " ").strip(),
                    "authors": authors,
                    "year": year,
                    "abstract": "Preprint article in life and health sciences from bioRxiv / medRxiv.",
                    "doi": doi_url,
                    "url": doi_url,
                    "pdf_url": pdf_url,
                    "journal": "bioRxiv/medRxiv preprint",
                    "id": doi
                })
    except Exception as e:
        print(f"[bioRxiv error]: {e}")
    return papers

# ==========================================
# 7. Semantic Scholar Crawler
# ==========================================
def crawl_semantic_scholar(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    papers = []
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.parse.quote(query)}&limit={max_results}&fields=title,authors,year,abstract,openAccessPdf,externalIds,venue"
        res = requests.get(url, headers=DEFAULT_HEADERS, timeout=6)
        if res.status_code == 200:
            for item in res.json().get("data", []):
                title = item.get("title") or "Untitled"
                authors = [a.get("name") for a in item.get("authors", []) if a.get("name")]
                year = item.get("year") or "N/A"
                abstract = item.get("abstract") or ""
                oa = item.get("openAccessPdf") or {}
                pdf_url = oa.get("url")
                
                ext = item.get("externalIds") or {}
                doi = f"https://doi.org/{ext.get('DOI')}" if ext.get("DOI") else ""
                
                papers.append({
                    "source": "Semantic Scholar",
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "abstract": abstract,
                    "doi": doi,
                    "url": doi or f"https://www.semanticscholar.org/paper/{item.get('paperId')}",
                    "pdf_url": pdf_url,
                    "journal": item.get("venue") or "Semantic Scholar Index",
                    "id": item.get("paperId") or ""
                })
    except Exception:
        # Semantic Scholar rate limit is common, silently gracefully skip
        pass
    return papers

# ==========================================
# BibTeX Formatter
# ==========================================
def build_bibtex_entry(paper: Dict[str, Any]) -> str:
    """Generate a valid BibTeX citation string for a paper."""
    clean_title = re.sub(r'[{}]', '', paper.get("title", ""))
    first_author = paper.get("authors", ["Anonymous"])[0] if paper.get("authors") else "Anonymous"
    cite_key_author = re.sub(r'[^a-zA-Z]', '', first_author.split()[-1] if first_author else "Author")
    year_str = str(paper.get("year", "2026"))
    cite_key = f"{cite_key_author.lower()}{year_str}_{sanitize_filename(clean_title)[:12]}"
    
    author_list = " and ".join(paper.get("authors", [])[:10]) if paper.get("authors") else "Anonymous"
    journal = paper.get("journal", "Academic Publication")
    doi = paper.get("doi", "")
    url = paper.get("url", "")
    
    entry = f"""@article{{{cite_key},
  title = {{{clean_title}}},
  author = {{{author_list}}},
  journal = {{{journal}}},
  year = {{{year_str}}},
  doi = {{{doi}}},
  url = {{{url}}}
}}"""
    return entry

# ==========================================
# Main Aggregator & Multi-Source Orchestrator
# ==========================================
def crawl_and_download_all(
    query: str,
    num_papers: int = 5,
    target_folder: str = "OUTPUT/Papers",
    sources: str = "all",
    download_pdf: bool = True
) -> str:
    """
    Crawls research papers across 7 scientific databases, downloads Open Access PDFs,
    and writes references.bib automatically.
    """
    abs_folder = os.path.abspath(target_folder)
    os.makedirs(abs_folder, exist_ok=True)
    
    sources_req = [s.strip().lower() for s in sources.split(",") if s.strip()]
    use_all = "all" in sources_req or not sources_req
    
    per_source = max(2, (num_papers // 3) + 1) if use_all else num_papers
    all_papers: List[Dict[str, Any]] = []
    
    print(f"[Crawler] Mencari paper untuk query '{query}' (Target: {num_papers} paper)...")
    
    # 1. arXiv
    if use_all or "arxiv" in sources_req:
        all_papers.extend(crawl_arxiv(query, max_results=per_source))
        
    # 2. OpenAlex
    if use_all or "openalex" in sources_req:
        all_papers.extend(crawl_openalex(query, max_results=per_source))
        
    # 3. Crossref
    if use_all or "crossref" in sources_req:
        all_papers.extend(crawl_crossref(query, max_results=per_source))
        
    # 4. PubMed & PMC
    if use_all or "pubmed" in sources_req or "pmc" in sources_req:
        all_papers.extend(crawl_pubmed_pmc(query, max_results=per_source))
        
    # 5. Europe PMC
    if use_all or "europepmc" in sources_req or "europe_pmc" in sources_req:
        all_papers.extend(crawl_europe_pmc(query, max_results=per_source))
        
    # 6. bioRxiv & medRxiv
    if use_all or "biorxiv" in sources_req or "medrxiv" in sources_req:
        all_papers.extend(crawl_biorxiv_medrxiv(query, max_results=per_source))

    # 7. Semantic Scholar
    if use_all or "semanticscholar" in sources_req or "semantic_scholar" in sources_req:
        all_papers.extend(crawl_semantic_scholar(query, max_results=per_source))

    if not all_papers:
        return f"Tidak ditemukan paper untuk query: '{query}' dari sumber: {sources}."

    # Deduplikasi berdasarkan kemiripan judul
    unique_papers = []
    seen_titles = set()
    for p in all_papers:
        norm_title = re.sub(r'[^a-zA-Z0-9]', '', p["title"].lower())[:60]
        if norm_title not in seen_titles and norm_title:
            seen_titles.add(norm_title)
            unique_papers.append(p)
            
    # Batasi ke jumlah yang diminta pengguna
    selected_papers = unique_papers[:num_papers]
    
    # Proses download PDF dan kompilasi laporan
    downloaded_count = 0
    results_info = []
    bibtex_entries = []
    
    for idx, p in enumerate(selected_papers, 1):
        pdf_path = None
        pdf_url = p.get("pdf_url")
        
        # Jika belum ada pdf_url langsung, coba cari lewat Unpaywall jika ada DOI
        if not pdf_url and p.get("doi"):
            pdf_url = resolve_unpaywall_pdf(p["doi"])
            if pdf_url:
                p["pdf_url"] = pdf_url
                
        if download_pdf and pdf_url:
            clean_name = sanitize_filename(p["title"])
            target_file = os.path.join(abs_folder, f"{idx:02d}_{clean_name}.pdf")
            success = download_pdf_file(pdf_url, target_file)
            if success:
                pdf_path = target_file
                downloaded_count += 1
                
        # Format informasi untuk LLM dan pengguna
        author_text = ", ".join(p["authors"][:4]) if p["authors"] else "Penulis tidak tercantum"
        if len(p["authors"]) > 4:
            author_text += " et al."
            
        abstract_snippet = p["abstract"][:350] + "..." if len(p["abstract"]) > 350 else (p["abstract"] or "Abstrak tidak tersedia.")
        
        info = f"[{idx}] {p['title']}\n"
        info += f"    - Sumber: {p['source']} | Tahun: {p['year']} | Jurnal: {p['journal']}\n"
        info += f"    - Penulis: {author_text}\n"
        info += f"    - DOI/Tautan: {p['doi'] or p['url']}\n"
        info += f"    - Berkas PDF: {pdf_path if pdf_path else ('Tautan: ' + pdf_url if pdf_url else 'Hanya Abstrak / Berbayar')}\n"
        info += f"    - Ringkasan: {abstract_snippet}"
        results_info.append(info)
        
        bibtex_entries.append(build_bibtex_entry(p))

    # Tulis berkas references.bib
    bib_path = os.path.join(abs_folder, "references.bib")
    try:
        with open(bib_path, "w", encoding="utf-8") as f:
            f.write("% Generated by V.E.R.A. 2.0 Academic Crawler\n\n")
            f.write("\n\n".join(bibtex_entries))
            f.write("\n")
    except Exception as e:
        print(f"[BibTeX write error]: {e}")

    # Susun laporan akhir
    report = f"[SUKSES] CRAWLING SELESAI ({len(selected_papers)} paper ditemukan dari {len(all_papers)} hasil pencarian)\n"
    report += f"- Lokasi Folder: {abs_folder}\n"
    report += f"- Berkas PDF Terunduh: {downloaded_count} PDF\n"
    report += f"- Berkas BibTeX: {bib_path}\n\n"
    report += "=== DAFTAR PAPER RISET ===\n\n"
    report += "\n\n".join(results_info) + "\n\n"
    report += "=== DATA BIBTEX LENGKAP ===\n\n" + "\n\n".join(bibtex_entries[:3])
    if len(bibtex_entries) > 3:
        report += f"\n\n... ({len(bibtex_entries) - 3} entri BibTeX lainnya tersimpan di {bib_path})"
        
    return report

if __name__ == "__main__":
    # Test run
    test_report = crawl_and_download_all("CRISPR gene editing", num_papers=3, target_folder="OUTPUT/Test_Crawler", sources="all")
    print(test_report)
