# Multi-Tenant Cloud Storage Migration Implementation Plan

## Executive Summary

This document outlines the comprehensive migration of the LLM-RAG-Longevity-Coach from a single-tenant, local storage application to a multi-tenant, cloud-based system with user-controlled encryption. The migration involves fundamental architectural changes to support user authentication, data isolation, cloud storage, and secure encryption.

## Current Architecture Analysis

### Single-Tenant Limitations
- **Global Singleton Vector Store**: `@st.cache_resource` creates shared vector store for all users
- **Shared File System**: All users access same `docs.jsonl` and `vector_store_data/`
- **No User Context**: Zero authentication or session isolation
- **Global Configuration**: Single config instance serves all users
- **Shared Resources**: LLM instances and processing resources shared across all users

### Key Components Requiring Refactoring
1. **Vector Store Management** (`coach/langchain_vector_store.py`)
2. **Document Processing** (`coach/langchain_document_processor.py`)
3. **Configuration System** (`coach/config.py`)
4. **Main Application** (`app.py`)
5. **All UI Pages** (`pages/`)
6. **Storage and Utilities** (`coach/utils.py`)

## Implementation Phases

### Phase 1: Foundation & Authentication System

#### 1.1 OAuth2 Integration
**Timeline**: 1-2 weeks
**Dependencies**: None

**Implementation Steps**:
1. **Install Authentication Dependencies**
   ```bash
   pip install streamlit-authenticator google-auth google-auth-oauthlib google-auth-httplib2
   ```

2. **Create Authentication Module** (`coach/auth.py`)
   ```python
   class AuthenticationManager:
       def __init__(self):
           self.oauth_config = self._load_oauth_config()
       
       def authenticate_user(self) -> Optional[UserContext]:
           """Handle OAuth2 flow and return user context"""
           pass
       
       def get_user_context(self) -> Optional[UserContext]:
           """Get current user context from session"""
           pass
   ```

3. **Create User Context Model** (`coach/models.py`)
   ```python
   class UserContext(BaseModel):
       user_id: str
       email: str
       name: str
       oauth_token: str
       refresh_token: str
       encryption_key: Optional[str] = None
   ```

4. **Update Configuration** (`coach/config.py`)
   ```python
   # Add OAuth2 configuration
   GOOGLE_CLIENT_ID: str = Field(default="")
   GOOGLE_CLIENT_SECRET: str = Field(default="")
   OAUTH_REDIRECT_URI: str = Field(default="http://localhost:8501/callback")
   ```

#### 1.2 User Session Management
**Timeline**: 1 week
**Dependencies**: Authentication module

**Implementation Steps**:
1. **Create Session Manager** (`coach/session.py`)
   ```python
   class SessionManager:
       def __init__(self):
           self.session_key = "user_context"
       
       def set_user_context(self, user_context: UserContext):
           st.session_state[self.session_key] = user_context
       
       def get_user_context(self) -> Optional[UserContext]:
           return st.session_state.get(self.session_key)
   ```

2. **Update Main App** (`app.py`)
   - Add authentication check at app entry
   - Implement login/logout flow
   - Add user context propagation

#### 1.3 Protected Routes & UI
**Timeline**: 1 week
**Dependencies**: Session management

**Implementation Steps**:
1. **Create Authentication Decorator**
   ```python
   def require_authentication(func):
       def wrapper(*args, **kwargs):
           if not session_manager.get_user_context():
               st.error("Please log in to access this page")
               return
           return func(*args, **kwargs)
       return wrapper
   ```

2. **Integrate Login Flow** (OAuth2 login integrated into main app)
3. **Add User Profile Management**
4. **Update Navigation with User Context**

### Phase 2: Multi-Tenant Architecture

#### 2.1 Tenant Isolation System
**Timeline**: 2-3 weeks
**Dependencies**: Authentication system

**Implementation Steps**:
1. **Create Tenant Context Manager** (`coach/tenant.py`)
   ```python
   class TenantManager:
       def __init__(self, user_context: UserContext):
           self.user_context = user_context
           self.tenant_id = user_context.user_id
       
       def get_tenant_path(self, path: str) -> str:
           """Get tenant-specific path"""
           return f"user_data/{self.tenant_id}/{path}"
       
       def get_vector_store_path(self) -> str:
           return self.get_tenant_path("vector_store")
       
       def get_documents_path(self) -> str:
           return self.get_tenant_path("docs.jsonl")
   ```

2. **Update Directory Structure**
   ```
   user_data/
   ├── {user_id_1}/
   │   ├── docs.jsonl
   │   ├── vector_store/
   │   │   ├── faiss_index.bin
   │   │   └── documents.pkl
   │   └── config/
   │       └── user_config.json
   ├── {user_id_2}/
   │   └── ...
   ```

#### 2.2 Tenant-Aware Vector Store
**Timeline**: 2 weeks
**Dependencies**: Tenant isolation system

**Implementation Steps**:
1. **Refactor Vector Store** (`coach/langchain_vector_store.py`)
   ```python
   class TenantAwareLangChainVectorStore(LangChainVectorStore):
       def __init__(self, tenant_manager: TenantManager, config: Config):
           self.tenant_manager = tenant_manager
           self.vector_store_path = tenant_manager.get_vector_store_path()
           super().__init__(config)
       
       def _get_faiss_index_path(self) -> str:
           return os.path.join(self.vector_store_path, "faiss_index.bin")
   ```

2. **Update Vector Store Factory** (`coach/vector_store_factory.py`)
   ```python
   def create_vector_store(tenant_manager: TenantManager, config: Config) -> LangChainVectorStore:
       return TenantAwareLangChainVectorStore(tenant_manager, config)
   ```

3. **Implement Resource Pooling**
   - LRU cache for vector stores
   - Memory management for concurrent users
   - Lazy loading and cleanup

#### 2.3 Tenant-Aware Document Processing
**Timeline**: 1-2 weeks
**Dependencies**: Tenant-aware vector store

**Implementation Steps**:
1. **Update Document Processor** (`coach/langchain_document_processor.py`)
   ```python
   class TenantAwareDocumentProcessor(LangChainDocumentProcessor):
       def __init__(self, tenant_manager: TenantManager, config: Config):
           self.tenant_manager = tenant_manager
           super().__init__(config)
       
       def save_documents(self, documents: List[Document]) -> None:
           docs_path = self.tenant_manager.get_documents_path()
           # Ensure tenant directory exists
           os.makedirs(os.path.dirname(docs_path), exist_ok=True)
           # Save to tenant-specific location
   ```

2. **Update Utilities** (`coach/utils.py`)
   - Tenant-aware JSONL operations
   - User-specific document loading
   - Tenant-isolated file operations

### Phase 3: Cloud Storage & Encryption

#### 3.1 GCP Cloud Storage Integration
**Timeline**: 2-3 weeks
**Dependencies**: Multi-tenant architecture

**Implementation Steps**:
1. **Install GCP Dependencies**
   ```bash
   pip install google-cloud-storage google-auth
   ```

2. **Create Storage Abstraction** (`coach/storage/base.py`)
   ```python
   class StorageProvider(ABC):
       @abstractmethod
       def upload_file(self, local_path: str, remote_path: str) -> None:
           pass
       
       @abstractmethod
       def download_file(self, remote_path: str, local_path: str) -> None:
           pass
       
       @abstractmethod
       def delete_file(self, remote_path: str) -> None:
           pass
   ```

3. **Implement GCP Storage Provider** (`coach/storage/gcp.py`)
   ```python
   class GCPStorageProvider(StorageProvider):
       def __init__(self, bucket_name: str, credentials_path: str):
           self.client = storage.Client.from_service_account_json(credentials_path)
           self.bucket = self.client.bucket(bucket_name)
       
       def upload_file(self, local_path: str, remote_path: str) -> None:
           blob = self.bucket.blob(remote_path)
           blob.upload_from_filename(local_path)
   ```

4. **Create Local Storage Provider** (`coach/storage/local.py`)
   ```python
   class LocalStorageProvider(StorageProvider):
       def upload_file(self, local_path: str, remote_path: str) -> None:
           shutil.copy2(local_path, remote_path)
   ```

#### 3.2 Client-Side Encryption System
**Timeline**: 2-3 weeks
**Dependencies**: GCP storage integration

**Implementation Steps**:
1. **Install Encryption Dependencies**
   ```bash
   pip install cryptography argon2-cffi
   ```

2. **Create Encryption Module** (`coach/encryption.py`)
   ```python
   class EncryptionManager:
       def __init__(self, user_context: UserContext):
           self.user_context = user_context
           self.encryption_key = self._derive_encryption_key()
       
       def _derive_encryption_key(self) -> bytes:
           """Derive encryption key from user OAuth data + password"""
           pass
       
       def encrypt_file(self, file_path: str) -> str:
           """Encrypt file and return encrypted file path"""
           pass
       
       def decrypt_file(self, encrypted_path: str) -> str:
           """Decrypt file and return decrypted file path"""
           pass
   ```

3. **Key Derivation Strategy**
   ```python
   def _derive_encryption_key(self) -> bytes:
       # Combine OAuth user ID with user-provided password
       salt = hashlib.sha256(self.user_context.user_id.encode()).digest()
       password = self._get_user_password()  # Prompt user for password
       
       # Use Argon2id for key derivation
       argon2 = argon2_cffi.PasswordHasher()
       key = argon2.hash(password.encode(), salt=salt)
       return key[:32]  # AES-256 key
   ```

4. **Integrate Encryption with Storage**
   ```python
   class EncryptedStorageProvider:
       def __init__(self, storage_provider: StorageProvider, encryption_manager: EncryptionManager):
           self.storage_provider = storage_provider
           self.encryption_manager = encryption_manager
       
       def upload_encrypted_file(self, local_path: str, remote_path: str) -> None:
           encrypted_path = self.encryption_manager.encrypt_file(local_path)
           self.storage_provider.upload_file(encrypted_path, remote_path)
   ```

#### 3.3 Encrypted Vector Store Persistence
**Timeline**: 1-2 weeks
**Dependencies**: Encryption system

**Implementation Steps**:
1. **Update Vector Store for Encryption**
   ```python
   class EncryptedTenantAwareVectorStore(TenantAwareLangChainVectorStore):
       def __init__(self, tenant_manager: TenantManager, encryption_manager: EncryptionManager, config: Config):
           self.encryption_manager = encryption_manager
           super().__init__(tenant_manager, config)
       
       def save_vector_store(self) -> None:
           # Save to local temp file
           temp_path = self._save_to_temp()
           # Encrypt and upload
           encrypted_path = self.encryption_manager.encrypt_file(temp_path)
           self.storage_provider.upload_file(encrypted_path, self.remote_path)
   ```

2. **Implement Secure Loading**
   - Download encrypted files to temp location
   - Decrypt on-the-fly during loading
   - Secure cleanup of temporary files

### Phase 4: Application Refactoring

#### 4.1 Main Application Updates
**Timeline**: 1-2 weeks
**Dependencies**: All previous phases

**Implementation Steps**:
1. **Refactor Main App** (`app.py`)
   ```python
   def main():
       # Initialize authentication
       auth_manager = AuthenticationManager()
       user_context = auth_manager.get_user_context()
       
       if not user_context:
           show_login_page()
           return
       
       # Initialize tenant-aware components
       tenant_manager = TenantManager(user_context)
       encryption_manager = EncryptionManager(user_context)
       storage_provider = create_storage_provider(user_context)
       
       # Create tenant-aware vector store
       vector_store = create_tenant_vector_store(tenant_manager, encryption_manager, storage_provider)
       
       # Continue with application logic...
   ```

2. **Update Session State Management**
   - Remove global caching decorators
   - Implement per-user resource caching
   - Add proper cleanup on logout

#### 4.2 UI Pages Refactoring
**Timeline**: 2-3 weeks
**Dependencies**: Main application updates

**Implementation Steps**:
1. **Update Knowledge Base Page** (`pages/1_Knowledge_Base.py`)
   ```python
   @require_authentication
   def show_knowledge_base():
       user_context = session_manager.get_user_context()
       tenant_manager = TenantManager(user_context)
       
       # Load user-specific documents
       documents = load_user_documents(tenant_manager)
       
       # Show tenant-specific data...
   ```

2. **Update Upload Documents Page** (`pages/2_Upload_Documents.py`)
   - Add tenant-aware file upload
   - Implement encrypted storage
   - Add progress indicators for cloud operations

3. **Update Guided Entry Page** (`pages/3_Guided_Entry.py`)
   - Use tenant-aware document processing
   - Add user-specific data validation
   - Implement cloud sync indicators

#### 4.3 Configuration Management
**Timeline**: 1 week
**Dependencies**: UI refactoring

**Implementation Steps**:
1. **Create User Configuration System** (`coach/user_config.py`)
   ```python
   class UserConfig(BaseModel):
       user_id: str
       preferred_model: str
       search_settings: Dict[str, Any]
       encryption_settings: Dict[str, Any]
   ```

2. **Implement Per-User Settings Storage**
   - Store in encrypted cloud storage
   - Provide default configurations
   - Allow user customization

### Phase 5: Migration & Testing

#### 5.1 Data Migration Strategy
**Timeline**: 1-2 weeks
**Dependencies**: Complete refactored system

**Implementation Steps**:
1. **Create Migration Script** (`scripts/migrate_to_multi_tenant.py`)
   ```python
   def migrate_single_tenant_data():
       # Create admin user for existing data
       admin_user = UserContext(
           user_id="admin",
           email="admin@localhost",
           name="Admin User"
       )
       
       # Move existing data to admin user folder
       # Encrypt and upload to cloud storage
       # Update vector store references
   ```

2. **Backup and Recovery**
   - Create backup of existing data
   - Implement rollback procedures
   - Test migration on copy of data

#### 5.2 Security Testing
**Timeline**: 1-2 weeks
**Dependencies**: Migration completed

**Testing Areas**:
1. **Authentication Security**
   - OAuth2 flow security
   - Session management
   - Token refresh handling

2. **Encryption Validation**
   - Key derivation security
   - File encryption/decryption
   - Secure key storage

3. **Tenant Isolation**
   - Data access controls
   - Cross-tenant data leakage
   - Resource isolation

#### 5.3 Performance Testing
**Timeline**: 1 week
**Dependencies**: Security testing

**Testing Areas**:
1. **Multi-User Load Testing**
   - Concurrent user scenarios
   - Resource utilization
   - Response times

2. **Cloud Storage Performance**
   - Upload/download speeds
   - Encryption overhead
   - Caching effectiveness

## Technical Architecture

### Security Architecture
```
User OAuth → Key Derivation → Client-Side Encryption → GCP Storage
     ↓              ↓                    ↓                  ↓
Session Mgmt → Tenant Context → Encrypted Files → Cloud Backup
```

### Data Flow
```
User Login → OAuth2 Flow → User Context → Tenant Manager → Encrypted Storage
     ↓           ↓             ↓              ↓                ↓
Vector Store ← Decryption ← Cloud Download ← Tenant Path ← User Query
```

### Component Dependencies
```
Authentication → Session Management → Tenant Isolation → Storage Abstraction → Encryption
                                                              ↓
                                                     Cloud Storage Integration
```

## Configuration Changes

### New Environment Variables
```bash
# OAuth2 Configuration
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
OAUTH_REDIRECT_URI=http://localhost:8501/callback

# GCP Configuration
GCP_PROJECT_ID=your_project_id
GCP_BUCKET_NAME=longevity-coach-data
GCP_CREDENTIALS_PATH=/path/to/service-account.json

# Storage Configuration
STORAGE_BACKEND=gcp  # or 'local' for development
ENABLE_ENCRYPTION=true
ENCRYPTION_ALGORITHM=AES-GCM

# Multi-Tenant Configuration
MAX_CONCURRENT_USERS=10
VECTOR_STORE_CACHE_SIZE=5
USER_DATA_ROOT=user_data/
```

## Risk Assessment & Mitigation

### High-Risk Areas
1. **Data Migration**: Risk of data loss during migration
   - **Mitigation**: Comprehensive backup and rollback procedures

2. **Encryption Key Management**: Risk of key loss or compromise
   - **Mitigation**: Multiple key derivation sources, recovery mechanisms

3. **Performance Impact**: Risk of degraded performance with cloud storage
   - **Mitigation**: Intelligent caching, connection pooling

### Medium-Risk Areas
1. **Authentication Issues**: OAuth2 integration complexity
   - **Mitigation**: Thorough testing, fallback mechanisms

2. **Tenant Isolation**: Risk of data leakage between tenants
   - **Mitigation**: Comprehensive isolation testing

## Success Criteria

### Functional Requirements
- [ ] Users can authenticate via Google OAuth2
- [ ] Each user has isolated data storage
- [ ] Data is encrypted with user-controlled keys
- [ ] Vector stores work correctly per tenant
- [ ] Cloud storage integration functions properly
- [ ] All existing features work in multi-tenant mode

### Non-Functional Requirements
- [ ] Response times < 2 seconds for cached operations
- [ ] Support for 10+ concurrent users
- [ ] 99.9% uptime for cloud storage operations
- [ ] Zero data leakage between tenants
- [ ] Secure key management and encryption

### Security Requirements
- [ ] OAuth2 tokens properly secured
- [ ] Encryption keys never stored in plaintext
- [ ] All data encrypted at rest
- [ ] Proper session management
- [ ] Tenant isolation verified

## Timeline Summary

**Total Estimated Duration**: 12-16 weeks

- **Phase 1**: 3-4 weeks (Authentication & Foundation)
- **Phase 2**: 4-5 weeks (Multi-Tenant Architecture)
- **Phase 3**: 4-5 weeks (Cloud Storage & Encryption)
- **Phase 4**: 3-4 weeks (Application Refactoring)
- **Phase 5**: 2-3 weeks (Migration & Testing)

## Next Steps

1. **Environment Setup**
   - Set up GCP project and service account
   - Configure OAuth2 credentials
   - Install required dependencies

2. **Development Environment**
   - Create development branch
   - Set up testing environment
   - Implement basic authentication

3. **Incremental Implementation**
   - Start with Phase 1 (Authentication)
   - Test each phase thoroughly before proceeding
   - Maintain backward compatibility during development

This plan provides a comprehensive roadmap for transforming the LLM-RAG-Longevity-Coach into a secure, multi-tenant, cloud-based application with user-controlled encryption.