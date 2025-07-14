import logging
import os
from sentence_transformers import SentenceTransformer
import faiss
import fitz  # PyMuPDF for PDF loading

# Configure Logger
os.makedirs("logs", exist_ok=True)  # Ensure logs directory exists
pdf_logger = logging.getLogger("pdf_loader")
pdf_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("logs/pdf_loader_logs.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
pdf_logger.addHandler(file_handler)

# Load SentenceTransformer model
model = SentenceTransformer('all-MiniLM-L6-v2')
faiss_index_path = "faiss_index"
pdf_dir = "data"  # Directory containing PDFs

# Custom text splitter function
def split_text(text, chunk_size=500, chunk_overlap=100):
    """
    Split text into chunks of specified size with overlap.
    
    Args:
        text (str): The input text to split.
        chunk_size (int): Maximum size of each chunk.
        chunk_overlap (int): Number of characters to overlap between chunks.
    
    Returns:
        list: List of text chunks.
    """
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        # Adjust end to avoid splitting in the middle of a word
        if end < text_length:
            while end > start and text[end] not in (" ", "\n", "\t"):
                end -= 1
            if end == start:  # If we can't find a space, force split at chunk_size
                end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:  # Only add non-empty chunks
            chunks.append(chunk)
        start = end - chunk_overlap if end < text_length else end
    
    return chunks

try:
    if os.path.exists(faiss_index_path):
        pdf_logger.info("FAISS index already exists. Delete the directory to recreate.")
        print("FAISS index already exists. Delete the directory to recreate.")
    else:
        pdf_logger.info("Creating new FAISS index...")
        
        # Ensure PDF directory exists
        if not os.path.exists(pdf_dir):
            raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")

        # Load all PDFs from the directory
        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found in {pdf_dir}")

        all_texts = []
        for pdf_file in pdf_files:
            pdf_path = os.path.join(pdf_dir, pdf_file)
            pdf_logger.info(f"Processing {pdf_path}...")
            
            # Extract text from PDF
            pdf_document = fitz.open(pdf_path)
            full_text = ""
            for page in pdf_document:
                full_text += page.get_text() + "\n"
            pdf_document.close()

            # Split text into chunks
            chunks = split_text(full_text, chunk_size=500, chunk_overlap=100)
            all_texts.extend(chunks)

        if not all_texts:
            raise ValueError("No text extracted from PDFs.")

        # Generate embeddings
        pdf_logger.info("Generating embeddings...")
        embeddings = model.encode(all_texts, show_progress_bar=True)
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)

        # Save the index and texts
        os.makedirs(faiss_index_path, exist_ok=True)
        faiss.write_index(index, os.path.join(faiss_index_path, "index.faiss"))
        with open(os.path.join(faiss_index_path, "texts.txt"), "w", encoding="utf-8") as f:
            for text in all_texts:
                f.write(text + "\n---\n")

        pdf_logger.info("FAISS index created and saved successfully.")
        print("FAISS index created and saved successfully.")

except Exception as e:
    pdf_logger.error(f"FAISS Index Creation Error: {e}")
    print(f"FAISS Index Creation Error: {e}")
    raise