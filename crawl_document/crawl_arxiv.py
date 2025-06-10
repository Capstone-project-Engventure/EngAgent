import arxiv
from pathlib import Path
import os

out_dir = Path("data/arxiv")
out_dir.mkdir(parents=True, exist_ok=True)

# 1. Chỉ khởi tạo page_size và (tuỳ chọn) num_retries
client = arxiv.Client(
    page_size=100,  # max 100 kết quả/trang
    num_retries=5,  # retry 5 lần nếu gặp lỗi mạng
)
search = arxiv.Search(
    query="English language learning",
    max_results=100,
    sort_by=arxiv.SortCriterion.SubmittedDate,
)

for result in client.results(search):
    print(f"{result.title}\n{result.pdf_url}\n")
    paper_id = result.entry_id.split("/")[-1]  # e.g. "2506.06281v1"
    filename = f"{paper_id}.pdf"  # e.g. "2506.06281v1.pdf"
    pdf_path = out_dir / filename
    if not pdf_path.exists():
        # <-- note the two keyword args here:
        result.download_pdf(dirpath=str(out_dir), filename=filename)
        print(f"Downloaded {filename}")
    else:
        print(f"Already have {filename}")
