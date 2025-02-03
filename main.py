import sqlite3
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
import os
from xml_to_db import add_data_to_db
import shutil
# ---------------------------------------------
# Function to load data from the SQLite database
# ---------------------------------------------
def load_db_data(db_path: str) -> list[Document]:
    add_data_to_db()
    documents = []

    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()

            # Query 'track_stats' table
            cur.execute(
                "SELECT distance, timer_time, total_elapsed_time, moving_time, ascent, descent, calories, avg_heart_rate, avg_cadence FROM track_stats"
            )
            stat_row = cur.fetchone()
            if stat_row:
                stat_doc_content = (
                    "**Track Statistics**:\n\n"
                    f"Distance: {stat_row[0]} meters\n"
                    f"Timer Time: {stat_row[1]} seconds\n"
                    f"Total Elapsed Time: {stat_row[2]} seconds\n"
                    f"Moving Time: {stat_row[3]} seconds\n"
                    f"Ascent: {stat_row[4]} meters\n"
                    f"Descent: {stat_row[5]} meters\n"
                    f"Calories: {stat_row[6]}\n"
                    f"Average Heart Rate: {stat_row[7]} bpm\n"
                    f"Average Cadence: {stat_row[8]} rpm\n"
                )
                documents.append(Document(page_content=stat_doc_content, metadata={"source": "track_stats"}))

            # Query 'track_points' table
            cur.execute("SELECT ele, time, temperature, hr, cad FROM track_points")
            track_points_rows = cur.fetchall()
            print(f"Found {len(track_points_rows)} track points in the database.")

            # Chunking track points for efficiency
            chunk_size = 100
            for idx in range(0, len(track_points_rows), chunk_size):
                chunk_rows = track_points_rows[idx: idx + chunk_size]
                content = "\n".join(
                    f"Elevation: {row[0]}, Time: {row[1]}, Temperature: {row[2]}, Heart Rate: {row[3]}, Cadence: {row[4]}"
                    for row in chunk_rows
                )
                documents.append(Document(page_content=content, metadata={"source": "track_points", "chunk": idx // chunk_size}))

    except Exception as e:
        print(f"Error reading from the database: {e}")

    return documents


# ---------------------------------------------
# Function to split long documents into smaller chunks
# ---------------------------------------------
def split_documents(documents: list[Document], chunk_size: int = 1000, chunk_overlap: int = 100) -> list[Document]:
    text_splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return [
        Document(page_content=chunk, metadata={**doc.metadata, "sub_chunk": i})
        for doc in documents
        for i, chunk in enumerate(text_splitter.split_text(doc.page_content))
    ]


# ---------------------------------------------
# Function to create a FAISS vector store from documents
# ---------------------------------------------
def create_vector_store(docs: list[Document],
                        embedding_model: str = "sentence-transformers/all-mpnet-base-v2") -> FAISS:
    try:
        embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        index_path = "faiss_index"

        # 🔥 Drop the existing FAISS index if it exists
        if os.path.exists(index_path):
            shutil.rmtree(index_path)  # Removes the directory and its contents
            print(f"Deleted existing FAISS index at '{index_path}'.")

        # Create a new FAISS index from documents
        return FAISS.from_documents(docs, embeddings)

    except Exception as e:
        print(f"Error creating vector store: {e}")
        return None


# ---------------------------------------------
# Function to retrieve track statistics manually from FAISS index
# ---------------------------------------------
def get_track_stats(vectorstore):
    """Retrieve the track_stats document manually from FAISS storage."""
    return next(
        (doc.page_content for doc in vectorstore.docstore._dict.values() if doc.metadata.get("source") == "track_stats"),
        None,
    )


# ---------------------------------------------
# Helper function to extract values from retrieved documents
# ---------------------------------------------
def extract_value(text, key):
    """Extracts a specific value from a document text using key matching."""
    for line in text.split("\n"):
        if key in line:
            return line.split(":")[-1].strip()
    return "Not available"


# ---------------------------------------------
# Function to construct structured query based on extracted values
# ---------------------------------------------
def retrieve_all_data(query, retriever, vectorstore):
    """Retrieves all relevant data and formats it into a clear prompt for the LLM."""
    retrieved_docs = retriever.get_relevant_documents(query)

    # Ensure track_stats is included
    track_stats = get_track_stats(vectorstore)
    if track_stats:
        retrieved_docs.insert(0, Document(page_content=track_stats, metadata={"source": "track_stats"}))

    # Extract relevant values for structured response
    extracted_values = {
        "Elevation Gain": extract_value(track_stats, "Ascent"),
        "Total Distance": extract_value(track_stats, "Distance"),
        "Average Heart Rate": extract_value(track_stats, "Average Heart Rate"),
        "Calories Burned": extract_value(track_stats, "Calories"),
        "Moving Time": extract_value(track_stats, "Moving Time"),
    }

    # Prepare natural-language prompt for LLM
    structured_query = f"""
You are an expert in analyzing hiking and fitness data. Below is structured data about a hike, including track statistics and detailed track points.

### **Track Statistics:**
- Elevation Gain: {extracted_values['Elevation Gain']} meters
- Total Distance: {extracted_values['Total Distance']} meters
- Average Heart Rate: {extracted_values['Average Heart Rate']} bpm
- Calories Burned: {extracted_values['Calories Burned']} kcal
- Moving Time: {extracted_values['Moving Time']} seconds

### **Detailed Track Data (Sample Points):**
{retrieved_docs[0].page_content[:500]}...

Using this information, please provide a **detailed summary** of the hike, including key insights. If any values are missing, estimate based on available data.

#### Example questions you can answer:
- What was the overall difficulty of the hike?
- How did the heart rate change over time?
- Were there any temperature fluctuations?
- What was the estimated number of steps taken?

**Now, please provide a detailed analysis.**
"""

    return structured_query


# ---------------------------------------------
# Main execution: Load data, build vector store, and query using RetrievalQA
# ---------------------------------------------
def main():
    db_path = "gpx_data.db"
    print("Loading data from database...")
    documents = load_db_data(db_path)

    if not documents:
        print("No documents loaded from the database.")
        return

    print("Splitting documents (if needed)...")
    docs_split = split_documents(documents)
    print(f"Total document chunks: {len(docs_split)}")

    print("Creating vector store...")
    vectorstore = create_vector_store(docs_split)
    if vectorstore is None:
        return

    index_path = "faiss_index"
    try:
        vectorstore.save_local(index_path)
        print(f"Vector store saved locally at '{index_path}'.")
    except Exception as e:
        print(f"Error saving vector store: {e}")

    try:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 100, "search_type": "similarity"})
        llm = Ollama(model="deepseek-r1:14b")
        qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)
    except Exception as e:
        print(f"Error setting up LLM or QA chain: {e}")
        return

    try:
        query = "Provide a detailed summary of the hike. Be sure to cover all relevant data points."
        combined_data = retrieve_all_data(query, retriever, vectorstore)

        result = qa_chain.run(combined_data)
        print("Query Result:\n", result)
    except Exception as e:
        print(f"An error occurred while running the query: {e}")


if __name__ == "__main__":
    main()
