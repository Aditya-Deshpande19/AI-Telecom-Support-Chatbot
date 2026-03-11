AI Technical Support RAG Agent

A Retrieval-Augmented Generation (RAG) Agent designed to provide accurate technical support responses using internal documentation.
The system retrieves relevant knowledge from a vector database and generates grounded answers using an LLM.

Built using:

LangChain

LangGraph

Chroma

Ollama

LLM: Qwen2.5

Project Overview

This project implements a production-style RAG pipeline for answering technical support queries.

Instead of relying solely on a language model, the system:

Stores documents in a vector database

Retrieves relevant knowledge using semantic search

Generates answers grounded in retrieved context

Uses grading and validation layers to reduce hallucinations

This approach improves accuracy, reliability, and explainability.

Features

Retrieval-Augmented Generation (RAG)

Semantic search using embeddings

Query rewriting for improved retrieval

Tool-calling agent architecture

Document relevance grading

Hallucination detection

Graph-based workflow using LangGraph

Streaming execution for debugging and monitoring

System Architecture

The pipeline follows these steps:

User Query Input

Query Rewriting

Embedding Generation

Vector Database Retrieval

Document Relevance Grading

Answer Generation

Hallucination Validation

Final Response Output

Workflow structure:

User Query
     ↓
Query Rewriter
     ↓
Vector Retrieval (Chroma)
     ↓
Document Grader
     ↓
Answer Generator
     ↓
Hallucination Check
     ↓
Final Response

The entire pipeline is orchestrated using LangGraph state workflows.

Project Structure
project/
│
├── data/
│   └── knowledge_base_documents
│
├── vector_db/
│   └── chroma_storage
│
├── notebooks/
│   └── rag_agent.ipynb
│
├── utils/
│   └── helper_functions
│
└── README.md
How It Works
1. Document Processing

Documents are split into smaller chunks to improve retrieval accuracy.

Chunking ensures that each piece of information can be retrieved independently.

2. Embedding Generation

Each chunk is converted into a vector representation using an embedding model.

These vectors represent the semantic meaning of text.

3. Vector Database Storage

The embeddings are stored inside a Chroma vector database.

This enables fast similarity search when a query is asked.

4. Query Rewriting

User queries may be vague or informal.

A rewriting step transforms the query into a clearer form that aligns better with stored knowledge.

Example:

User query:
"No internet"

Rewritten query:
"Jio Fiber internet troubleshooting steps"
5. Semantic Retrieval

The rewritten query is embedded and compared with stored vectors.

The top k most relevant documents are retrieved.

6. Document Grading

An LLM checks whether the retrieved documents are relevant to the user’s question.

If documents are not relevant, the query may be rewritten and retrieval retried.

7. Answer Generation

The language model generates a response using:

User question

Retrieved context

The prompt restricts answers to:

grounded information

concise responses

no fabrication

8. Hallucination Detection

A validation layer checks generated responses for:

vague language

unsupported claims

insufficient information

If the response fails validation, the pipeline can retry or reject the answer.

Example Query

Input:

Why is my Jio Fiber internet not working?

System retrieves troubleshooting steps and generates a response based on relevant documentation.

Applications

This architecture can be used for:

Customer support automation

Internal company knowledge assistants

Technical documentation search

AI help desks

Enterprise RAG systems

Key Concepts Demonstrated

This project demonstrates understanding of:

Retrieval-Augmented Generation

Vector databases

Semantic embeddings

Prompt engineering

Tool-calling agents

Graph-based AI workflows

Hallucination mitigation

Future Improvements

Possible enhancements include:

Multi-turn conversation memory

API deployment using FastAPI

Web interface for user interaction

Model evaluation using RAG benchmarks

Caching for faster retrieval

Authentication for enterprise usage

Author

Aditya Deshpande

AI / Machine Learning Projects and Experiments
