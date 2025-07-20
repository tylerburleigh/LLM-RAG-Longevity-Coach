# Advanced RAG-Powered Longevity Coach

[work in progress]

A secure multi-tenant RAG (Retrieval-Augmented Generation) application that delivers personalized health and longevity advice. Built with LangChain and Streamlit, it combines hybrid search capabilities with complete user data isolation, Google OAuth authentication, and optional cloud storage with client-side encryption.

## 🎯 Key Features

### 🔐 **Secure Multi-Tenant Authentication**
- **Google OAuth2 Integration:** Secure login with Google accounts
- **Complete Data Isolation:** Each user gets their own private knowledge base and vector store
- **Session Management:** Automatic session timeout and secure logout
- **Protected Routes:** All pages require authentication for access
- **Tenant Management:** Automatic tenant setup and resource isolation

### 🧠 **Advanced Multi-Tenant RAG System**
- **Hybrid Search:** Combines BM25 (keyword) and FAISS (semantic) search for optimal relevance
- **Per-User Vector Stores:** Each user has their own isolated FAISS index and document store
- **LangChain Integration:** Built on LangChain for extensible retrieval and processing
- **Multi-Strategy Retrieval:** Contextual compression and rank fusion for enhanced results
- **Real-Time Processing:** Live feedback during search planning and document processing
- **Tenant-Aware Caching:** Optional LRU caching for performance with complete isolation

### 📊 **Personal Knowledge Management**
- **Private Data Storage:** Each user's data completely isolated in their own directory
- **Interactive Data Editor:** Spreadsheet-like interface for personal knowledge base editing
- **Tenant-Aware PDF Processing:** Document uploads processed and stored per user
- **Guided Conversational Entry:** AI-assisted data entry through natural language chat
- **Automatic Re-indexing:** Seamless updates to user's private search indices when data changes

### 🔧 **Modern Multi-Tenant Architecture**
- **Complete Tenant Isolation:** Zero data leakage between users with separate file systems
- **Type-Safe Design:** Comprehensive Pydantic models and type hints throughout
- **Modular Components:** Clear separation of concerns with extensible provider system
- **Robust Error Handling:** Custom exception hierarchy with informative error messages
- **Configurable Settings:** Environment-driven configuration with sensible defaults
- **Backwards Compatibility:** Single-tenant mode still supported for development

### ☁️ **Cloud Storage & Encryption**
- **Google Cloud Storage Integration:** Optional GCP backend for scalable data storage
- **Client-Side Encryption:** AES-GCM encryption with user-controlled keys
- **Secure Key Derivation:** PBKDF2-based key derivation with automatic expiration
- **Connection Pooling:** Thread-safe GCP client pooling for performance
- **Intelligent Retry Logic:** Exponential backoff for transient failures
- **Rate Limiting:** Token bucket algorithm prevents encryption abuse
- **Comprehensive Audit Logging:** Track all security-sensitive operations

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
   
   # Optional: Cloud Storage (Phase 3)
   STORAGE_BACKEND=local  # Options: local, gcp
   GCP_PROJECT_ID=your_project_id
   GCP_BUCKET_NAME=longevity-coach-data
   GCP_CREDENTIALS_PATH=/path/to/service-account.json
   
   # Optional: Encryption (Phase 3)
   ENABLE_ENCRYPTION=false  # Enable client-side encryption
   KEY_DERIVATION_TTL=900  # Key cache TTL in seconds
   ```

4. **Set up Google OAuth2:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google+ API
   - Create OAuth2 credentials (Web application)
   - Add `http://localhost:8501/` to authorized redirect URIs
   - Copy the client ID and secret to your `.env` file

5. **(Optional) Set up Google Cloud Storage:**
   - Create a GCP project and enable the Cloud Storage API
   - Create a service account with Storage Admin permissions
   - Download the service account JSON key file
   - Create a GCS bucket for your data
   - Update `.env` with GCP configuration

6. **Run the application:**
   ```bash
   streamlit run app.py
   ```

### First Time Setup
1. Navigate to `http://localhost:8501`
2. Click "Login with Google" to authenticate
3. Once logged in, the system automatically creates your private tenant environment
4. You'll have access to all features with your own isolated knowledge base and vector store
5. Your data is completely separate from other users

## 📋 How It Works

The application provides two main workflows after authentication:

### 🗣️ **Chat Interface (Main Page)**
1. **Authentication Check:** Secure login required for access
2. **Tenant Isolation:** System loads your private knowledge base and vector store
3. **Query Analysis:** AI analyzes your health/longevity question
4. **Search Strategy:** System determines optimal search approach within your data
5. **Hybrid Retrieval:** Combines BM25 and FAISS search across your private documents
6. **Response Generation:** LLM generates personalized advice using your retrieved context
7. **Real-Time Feedback:** Live updates showing search and processing steps

### 📚 **Personal Knowledge Base Management**
Choose from multiple data input methods for your private knowledge base:

#### **Interactive Data Editor** (Knowledge Base page)
- Spreadsheet-like interface for editing your personal data
- Add, modify, or delete entries in your private knowledge base
- Automatic data validation and error handling
- One-click re-indexing of your personal search system

#### **PDF Document Upload** (Upload Documents page)
- Drag-and-drop PDF processing to your private storage
- LLM-powered text extraction and structuring
- Automatic conversion to structured knowledge entries in your database
- Progress tracking and error handling with tenant isolation

#### **Guided Conversational Entry** (Guided Entry page)
- Natural language data entry through chat interface
- AI assistant helps structure your personal information
- Review and approve entries before saving to your private database
- Perfect for adding personal health insights and experiences

## 🔧 Configuration Options

The application supports extensive configuration through environment variables:

### **Core Settings**
```env
# LLM Configuration
DEFAULT_LLM_MODEL=o3                    # OpenAI model to use
DEFAULT_TEMPERATURE=1.0                 # Response creativity (0.0-2.0)
GEMINI_API_KEY=your_key                 # Optional: for Gemini models

# Search Configuration
DEFAULT_TOP_K=5                         # Number of documents to retrieve per user
VECTOR_STORE_FOLDER=vector_store_data   # Legacy single-tenant storage (unused in multi-tenant)
EMBEDDING_MODEL=text-embedding-3-large  # OpenAI embedding model
VECTOR_STORE_CACHE_SIZE=5               # Multi-tenant vector store cache size

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
DOCS_FILE=docs.jsonl                   # Knowledge base file name (per tenant)
USER_DATA_ROOT=user_data               # Root directory for tenant data isolation
MAX_INSIGHTS=5                         # Maximum insights per query
MAX_CLARIFYING_QUESTIONS=3             # Maximum clarifying questions

# Security & Rate Limiting
RATE_LIMIT_OPERATIONS_PER_HOUR=100     # Max encryption operations per hour
RATE_LIMIT_BURST_SIZE=10               # Burst capacity for rate limiting
AUDIT_LOG_FILE=audit.log               # Security audit log location
```

## 🛡️ Security & Privacy

- **OAuth2 Security:** Industry-standard authentication with Google
- **Complete Data Isolation:** Each user's data stored in separate directories with no cross-access
- **Session Management:** Automatic timeout and secure logout
- **Client-Side Encryption:** Optional AES-GCM encryption with user-controlled keys
- **Secure Key Management:** PBKDF2 key derivation, no password storage, automatic expiration
- **API Key Protection:** Secure handling of OpenAI API keys
- **Input Validation:** Comprehensive validation of all user inputs
- **Protected Access:** All application features require authentication
- **Zero Data Leakage:** Architectural guarantees prevent cross-tenant data access
- **Audit Logging:** Comprehensive tracking of all security-sensitive operations
- **Rate Limiting:** Protection against encryption operation abuse

> **Multi-Tenant Architecture:** Each authenticated user gets completely isolated data storage including separate knowledge bases, vector stores, and configuration files. No user can access another user's data.

## 🏗️ Architecture

Built with modern Python technologies and multi-tenant architecture:

- **Frontend:** Streamlit for interactive web interface with authentication
- **Backend:** LangChain for RAG pipeline and tenant-aware document processing
- **Search:** Per-user FAISS indexes for vector similarity + BM25 for keyword matching
- **Authentication:** Google OAuth2 with secure session management and tenant isolation
- **Data Models:** Pydantic for type-safe data validation across all components
- **Storage:** Tenant-isolated JSONL files with optional GCP cloud storage backend
- **Encryption:** Client-side AES-GCM encryption with PBKDF2 key derivation
- **Security:** Comprehensive audit logging and rate limiting for sensitive operations
- **Multi-Tenancy:** Complete data isolation with `user_data/{user_id}/` directory structure

### 📁 Multi-Tenant Directory Structure

The application automatically creates isolated environments for each user:

```
user_data/
├── alice@example.com/         # User-specific directory
│   ├── docs.jsonl             # Personal knowledge base
│   ├── vector_store/          # Private FAISS index
│   │   └── faiss_index/
│   │       ├── index.faiss
│   │       └── index.pkl
│   └── config/                # User settings
│       └── user_config.json
├── bob@example.com/           # Another user's isolated data
│   ├── docs.jsonl
│   ├── vector_store/
│   └── config/
└── ...
```

**Key Benefits:**
- ✅ **Complete Isolation:** No data sharing between users
- ✅ **Automatic Creation:** Directories created on first login
- ✅ **Secure Access:** Each user can only access their own data
- ✅ **Independent Scaling:** Each user's data grows independently

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
- Ensure `USER_DATA_ROOT` directory is writable for tenant creation
- Check file permissions for individual user directories
- Verify PDF files are not corrupted during upload
- Each user's data is stored in `user_data/{user_id}/` with automatic directory creation

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

## 🚀 Future Roadmap

### Phase 3: Cloud Storage & Encryption ✅ (Implemented)
- **Cloud Storage Integration:** GCP storage backend with connection pooling
- **Client-Side Encryption:** AES-GCM encryption with user-controlled keys
- **Secure Key Management:** PBKDF2 key derivation with automatic expiration
- **Audit Logging:** Comprehensive security event tracking
- **Rate Limiting:** Token bucket algorithm for encryption operations
- **Intelligent Retry:** Exponential backoff for cloud operations

### Phase 4: Advanced Features (Planned)
- **Real-Time Collaboration:** Share specific knowledge entries with healthcare providers
- **Data Import/Export:** Import from health apps and export to various formats
- **Advanced Analytics:** Personal health insights and trend analysis
- **API Access:** Programmatic access to your personal health knowledge base

---

**Ready to get started with your own private longevity coach?** Follow the installation steps above and begin building your secure, personal health knowledge base today!
