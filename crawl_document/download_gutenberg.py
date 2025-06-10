# from gutenbergpy.gutenbergcache import GutenbergCache
# from gutenbergpy.textget import get_metadata, get_text_by_id, strip_headers
# from google.cloud import storage
# import os
# import tempfile

# # ------------------
# # CONFIGURATION
# # ------------------
# BUCKET_NAME = "engventure-rag-documents"
# SUBJECT = "English grammar"
# CREDENTIALS_PATH = "./engventure-credentials.json"

# # Thiết lập biến môi trường cho credentials
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH

# # ------------------
# # INITIALIZE GCS CLIENT
# # ------------------
# storage_client = storage.Client()
# bucket = storage_client.bucket(BUCKET_NAME)

# # ------------------
# # INITIALIZE GUTENBERG CACHE
# # ------------------
# if not GutenbergCache.exists():
#     # Tạo cache (download, unpack, parse, cache metadata)
#     GutenbergCache.create(download=True, unpack=True, parse=True, cache=True)
# cache = GutenbergCache.get_cache()

# # ------------------
# # FETCH E-TEXT IDs
# # ------------------
# etext_ids = cache.query(subjects=[SUBJECT])
# print(f"Found {len(etext_ids)} eText IDs for subject '{SUBJECT}': {etext_ids}")

# # ------------------
# # FETCH METADATA
# # ------------------
# metadata_records = get_metadata(etext_ids, fields=["title", "author"])
# print("Retrieved metadata for each text:")
# for rec in metadata_records:
#     print(f"{rec['title']} — {rec['author']}")

# # ------------------
# # DOWNLOAD & UPLOAD LOOP
# # ------------------
# for etext_id, rec in zip(etext_ids, metadata_records):
#     title = rec.get('title', '')
#     author = rec.get('author', '')
#     print(f"Processing eText ID: {etext_id} — {title} by {author}")

#     with tempfile.TemporaryDirectory() as tmpdir:
#         # Tải về raw text và loại bỏ header/footer
#         raw = get_text_by_id(etext_id)
#         text = strip_headers(raw)

#         # Lưu tạm nội dung
#         local_path = os.path.join(tmpdir, f"{etext_id}.txt")
#         with open(local_path, "wb") as f:
#             f.write(text)

#         # Upload lên GCS với metadata
#         blob = bucket.blob(f"gutenberg/{etext_id}.txt")
#         blob.metadata = {"title": title, "author": author}
#         blob.upload_from_filename(local_path)
#         blob.patch()

#         print(f"Uploaded {etext_id}.txt to gs://{BUCKET_NAME}/gutenberg/ with metadata.")

# print("All files uploaded successfully.")

import os

from gutenberg.acquire import get_metadata_cache
from gutenberg.query import get_etexts, get_metadata

# ------------------
# 1) KHỞI TẠO & POPULATE CACHE
# ------------------
cache = get_metadata_cache()
if not cache.exists:
    print("Cache chưa có, đang populate (có thể mất ~18h lần đầu)…")
    cache.populate()   # tải về và parse toàn bộ metadata :contentReference[oaicite:0]{index=0}
else:
    print("Cache đã sẵn sàng!")

# ------------------
# 2) LẤY E-TEXT IDs THEO SUBJECT
# ------------------
SUBJECT = "English grammar"
etext_ids = get_etexts('subject', SUBJECT)
print(f"Found {len(etext_ids)} eText IDs for subject '{SUBJECT}':")
print(etext_ids)  # ví dụ: frozenset({1234, 5678, …}) :contentReference[oaicite:1]{index=1}

# ------------------
# 3) IN TITLE & AUTHOR CỦA TỪNG TEXT
# ------------------
print("\nMetadata của các tài liệu:")
for eid in etext_ids:
    titles  = get_metadata('title',  eid)
    authors = get_metadata('author', eid)
    # get_metadata trả về frozenset, nên ta lấy phần tử đầu
    title  = next(iter(titles),  "Unknown title")
    author = next(iter(authors), "Unknown author")
    print(f"{eid}: {title} — {author}")
