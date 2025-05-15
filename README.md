# Conversational AI Bot for UT Dallas JSOM 
# https://jsom-botship.streamlit.app/

Welcome to the **Conversational AI Bot** project! This bot is designed to assist students, faculty, and staff at **UT Dallas Jindal School of Management (JSOM)** by providing answers to frequently asked questions (FAQs) about admissions, programs, scholarships, and general information related to JSOM.

## Objective
The goal of this project was to create a **go-to conversational bot** that can efficiently answer a wide range of FAQs related to **JSOM admissions**, **programs**, and **scholarships**. In addition, the bot is capable of handling questions that go beyond the scope of JSOM topics by expanding on the broader context of **UT Dallas**.

## Features
- **Answering FAQs**: The bot is equipped to respond to common queries about admissions, available programs, scholarship opportunities, and more.
- **Context Expansion**: If the question is outside the scope of JSOM, the bot intelligently expands on the context, offering relevant information related to the university or the school.
- **Interactive UI**: Built using **Streamlit**, providing an easy-to-use interface where users can interact with the bot.
- **Web Scraping**: The bot uses **web scraping** techniques to extract relevant data from the **UT Dallas JSOM** website, ensuring that it provides up-to-date and accurate answers.
- **Embedding for Fast Search**: The bot stores the data embeddings in **Pinecone**, enabling fast and efficient retrieval of information based on user queries.

## Tech Stack
- **Web Scraping**: 
  - `BeautifulSoup`, `requests`, and `Selenium` are used to scrape and collect data from relevant web pages.
  
- **Data Cleaning & Preprocessing**: 
  - `pandas` for data manipulation and cleaning.
  - `re` for regular expressions to clean up the data before embedding.

- **Chunking & Embedding**: 
  - `sentence-transformers` with the **all-MiniLM-L6-v2** model for generating embeddings from the scraped text.
  - **Pinecone** for storing and managing embeddings, enabling fast, real-time search capabilities.

- **Conversational Bot**:
  - **Streamlit** for the interactive web-based UI.
  - **OpenAI GPT-4o-mini** for generating responses to user queries, including both direct answers and context expansion.

## Setup Instructions
To get started with the project locally, follow these steps:

### 1. Clone the Repository
```bash
git clone https://github.com/PavanChandan29/Conversational-AI-Bot-for-UTDallas-JSOM-
cd Conversational-AI-Bot-for-UTDallas-JSOM-

pip install -r requirements.txt

streamlit run webapp.py

