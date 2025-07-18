# Advanced RAG-Powered Longevity Coach

[work in progress]

A secure RAG (Retrieval-Augmented Generation) application that delivers personalized health and longevity advice. Built with LangChain and Streamlit, it combines hybrid search capabilities with user-controlled data management and Google OAuth authentication.

## 🎯 Key Features

### 🔐 **Secure Authentication System**
- **Google OAuth2 Integration:** Secure login with Google accounts
- **Session Management:** Automatic session timeout and secure logout
- **Protected Routes:** All pages require authentication for access
- **User Context:** Maintains user identity throughout the application

### 🧠 **Advanced RAG System**
- **Hybrid Search:** Combines BM25 (keyword) and FAISS (semantic) search for optimal relevance
- **LangChain Integration:** Built on LangChain for extensible retrieval and processing
- **Multi-Strategy Retrieval:** Contextual compression and rank fusion for enhanced results
- **Real-Time Processing:** Live feedback during search planning and document processing

### 📊 **Flexible Knowledge Management**
- **Interactive Data Editor:** Spreadsheet-like interface for direct knowledge base editing
- **PDF Document Processing:** Automatic extraction and structuring of uploaded documents
- **Guided Conversational Entry:** AI-assisted data entry through natural language chat
- **Automatic Re-indexing:** Seamless updates to search indices when data changes

### 🔧 **Modern Architecture**
- **Type-Safe Design:** Comprehensive Pydantic models and type hints throughout
- **Modular Components:** Clear separation of concerns with extensible provider system
- **Robust Error Handling:** Custom exception hierarchy with informative error messages
- **Configurable Settings:** Environment-driven configuration with sensible defaults

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Google Cloud Project (for OAuth2 authentication)
- OpenAI API key (for LLM functionality)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/LLM-RAG-Longevity-Coach.git
   cd LLM-RAG-Longevity-Coach
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   # Required: OpenAI API key
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Required: Google OAuth2 credentials
   GOOGLE_CLIENT_ID=your_google_client_id_here
   GOOGLE_CLIENT_SECRET=your_google_client_secret_here
   OAUTH_REDIRECT_URI=http://localhost:8501/
   
   # Optional: Development settings
   OAUTH_INSECURE_TRANSPORT=true  # For local development
   ```

4. **Set up Google OAuth2:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google+ API
   - Create OAuth2 credentials (Web application)
   - Add `http://localhost:8501/` to authorized redirect URIs
   - Copy the client ID and secret to your `.env` file

5. **Run the application:**
   ```bash
   streamlit run app.py
   ```

### First Time Setup
1. Navigate to `http://localhost:8501`
2. Click "Login with Google" to authenticate
3. Once logged in, you'll have access to all features with your own private knowledge base

## 📋 How It Works

The application provides two main workflows after authentication:

### 🗣️ **Chat Interface (Main Page)**
1. **Authentication Check:** Secure login required for access
2. **Query Analysis:** AI analyzes your health/longevity question
3. **Search Strategy:** System determines optimal search approach
4. **Hybrid Retrieval:** Combines BM25 and FAISS search for maximum relevance
5. **Response Generation:** LLM generates personalized advice using retrieved context
6. **Real-Time Feedback:** Live updates showing search and processing steps

### 📚 **Knowledge Base Management**
Choose from multiple data input methods:

#### **Interactive Data Editor** (Knowledge Base page)
- Spreadsheet-like interface for direct editing
- Add, modify, or delete entries in real-time
- Automatic data validation and error handling
- One-click re-indexing of the search system

#### **PDF Document Upload** (Upload Documents page)
- Drag-and-drop PDF processing
- LLM-powered text extraction and structuring
- Automatic conversion to structured knowledge entries
- Progress tracking and error handling

#### **Guided Conversational Entry** (Guided Entry page)
- Natural language data entry through chat interface
- AI assistant helps structure your information
- Review and approve entries before saving
- Perfect for adding personal health insights

## 🔧 Configuration Options

The application supports extensive configuration through environment variables:

### **Core Settings**
```env
# LLM Configuration
DEFAULT_LLM_MODEL=o3                    # OpenAI model to use
DEFAULT_TEMPERATURE=1.0                 # Response creativity (0.0-2.0)
GOOGLE_API_KEY=your_key                 # Optional: for Gemini models

# Search Configuration
DEFAULT_TOP_K=5                         # Number of documents to retrieve
VECTOR_STORE_FOLDER=vector_store_data   # Local storage location
EMBEDDING_MODEL=text-embedding-3-large  # OpenAI embedding model

# Authentication
SESSION_TIMEOUT_HOURS=24                # Session timeout duration
OAUTH_INSECURE_TRANSPORT=true          # Enable for local development
```

### **Advanced Options**
```env
# Performance Tuning
RRF_K=60                               # Rank fusion parameter
SEARCH_MULTIPLIER=2                    # Search result multiplier
MAX_DOCUMENT_LENGTH=10000              # Document chunk size limit

# Data Management
DOCS_FILE=docs.jsonl                   # Knowledge base file name
MAX_INSIGHTS=5                         # Maximum insights per query
MAX_CLARIFYING_QUESTIONS=3             # Maximum clarifying questions
```

## 🛡️ Security & Privacy

- **OAuth2 Security:** Industry-standard authentication with Google
- **Session Management:** Automatic timeout and secure logout
- **Local Data Storage:** All user data stored locally (no cloud dependency)
- **API Key Protection:** Secure handling of OpenAI API keys
- **Input Validation:** Comprehensive validation of all user inputs
- **Protected Access:** All application features require authentication

> **Note:** This application currently uses a shared knowledge base for all authenticated users. Multi-tenant data isolation is planned for a future release.

## 🏗️ Architecture

Built with modern Python technologies:

- **Frontend:** Streamlit for interactive web interface
- **Backend:** LangChain for RAG pipeline and document processing
- **Search:** FAISS for vector similarity + BM25 for keyword matching
- **Authentication:** Google OAuth2 with secure session management
- **Data Models:** Pydantic for type-safe data validation
- **Storage:** Local JSONL files with automatic indexing

## 🚨 Troubleshooting

### Common Issues

**Authentication Problems:**
- Ensure Google OAuth2 credentials are correctly configured
- Check that redirect URI matches exactly (including trailing slash)
- Verify Google+ API is enabled in your GCP project

**Installation Issues:**
- Use Python 3.9+ for compatibility
- Install dependencies in a virtual environment
- Check that all required environment variables are set

**Performance Issues:**
- Increase `DEFAULT_TOP_K` for more comprehensive search
- Adjust `SEARCH_MULTIPLIER` for broader result sets
- Consider using a more powerful OpenAI model

**Data Management:**
- Ensure `DOCS_FILE` location is writable
- Check file permissions for `VECTOR_STORE_FOLDER`
- Verify PDF files are not corrupted during upload

### Getting Help

- Check the [Issues](https://github.com/yourusername/LLM-RAG-Longevity-Coach/issues) page for known problems
- Review the `CLAUDE.md` file for detailed technical documentation
- Examine application logs for specific error messages

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests, report bugs, or suggest new features.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [LangChain](https://langchain.com/) for RAG capabilities
- [Streamlit](https://streamlit.io/) for the web interface
- [OpenAI](https://openai.com/) for LLM and embedding models
- [Google Cloud](https://cloud.google.com/) for OAuth2 authentication
- [FAISS](https://github.com/facebookresearch/faiss) for vector similarity search

---

**Ready to get started with your personalized longevity coach?** Follow the installation steps above and begin building your own health knowledge base today!
