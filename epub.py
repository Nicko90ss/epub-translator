import os
import time
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup
import pdfplumber
from deep_translator import GoogleTranslator
from langdetect import detect

def extract_epub(file_path):
    book = epub.read_epub(file_path)
    texts = []
    for item in book.get_items():
        if item.get_type() == ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            texts.append(soup.get_text())
    return "\n".join(texts)

def extract_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def split_text(text, max_length):
    words = text.split()
    chunks = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 < max_length:
            current += " " + word
        else:
            chunks.append(current)
            current = word
    if current:
        chunks.append(current)
    return chunks

def translate_large_text(text, target="en", job_id=None, jobs=None):
    chunks = split_text(text, 1500)
    translated_chunks = []
    total = len(chunks)

    if job_id and jobs:
        jobs[job_id]['total'] = total

    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        if job_id and jobs:
            jobs[job_id]['progress'] = i + 1

        retry_count = 0
        while retry_count < 3:
            try:
                print(f"Translating chunk {i+1} of {total}...")
                translated = GoogleTranslator(source='auto', target=target).translate(chunk)
                translated_chunks.append(translated)
                time.sleep(2)
                break
            except Exception as e:
                retry_count += 1
                print(f"Retrying chunk {i+1}... ({retry_count}/3)")
                time.sleep(5)

        if retry_count == 3:
            translated_chunks.append("[TRANSLATION ERROR]")

    return "\n".join(translated_chunks)

def process_file_to_text(file_path, job_id=None, jobs=None):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".epub":
        text = extract_epub(file_path)
    elif ext == ".pdf":
        text = extract_pdf(file_path)
    else:
        return None
    if not text.strip():
        return None
    try:
        lang = detect(text[:2000])
        print(f"Detected language: {lang}")
        if job_id and jobs:
            jobs[job_id]['lang'] = lang
    except:
        pass
    return translate_large_text(text, job_id=job_id, jobs=jobs)

def process_file(file_input):
    clean_path = file_input.strip().replace('"', '').replace("'", "")
    if not os.path.exists(clean_path):
        print(f"Error: File not found at {clean_path}")
        return
    print(f"--- Processing: {os.path.basename(clean_path)} ---")
    result = process_file_to_text(clean_path)
    if result:
        with open("translated_output.txt", "w", encoding="utf-8") as f:
            f.write(result)
        print(f"\nSuccess! Saved as: translated_output.txt")

if __name__ == "__main__":
    path_input = input("Enter file path: ")
    process_file(path_input)
