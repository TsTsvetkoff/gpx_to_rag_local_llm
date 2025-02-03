📌 GPX Data Processor

This program processes a single GPX file at a time, extracting hiking statistics and track points, storing them in an SQLite database, and creating a FAISS vector store for further analysis.
🚀 How to Use
1️⃣ Add Your GPX File

Place your .gpx file inside the my_gpx_to_xml directory.
2️⃣ Run the Program

Execute the main script:

python main.py

📂 Project Structure

📁 project_root/
 ├── 📁 my_gpx_to_xml/      # Directory where you place your GPX file
 ├── 📁 parsed_xmls/        # Processed XML files
 ├── 📁 faiss_index/        # Vector store directory
 ├── gpx_data.db            # SQLite database storing hike data
 ├── main.py                # Main script to process the GPX file
 ├── requirements.txt       # Python dependencies
 ├── README.md              # This file!

🔧 Requirements

Ensure you have all dependencies installed:

pip install -r requirements.txt

📜 Description

    Parses a single GPX file from my_gpx_to_xml/
    Converts it into an XML format and extracts hiking data
    Stores the data into SQLite (gpx_data.db)
    Creates a FAISS vector store for advanced queries
    Supports LLM-based Q&A on hike data

💡 Notes

    The program only supports one GPX file at a time
    If you run the script multiple times, previous data will be overwritten
    Ensure your GPX file is valid and correctly formatted
