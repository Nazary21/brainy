# AI Bot Manager: System Specifications

## Project Overview
An intermediate API manager built in Python that connects multiple AI providers with various messaging platforms. The system supports customizable bot personalities, memory management, and extensible functionality through modules.

## Core Requirements

### AI Provider Integration
- Connect to multiple AI API providers:
  - OpenAI (GPT-4, etc.)
  - Grok
  - DeepSeek
  - Others (expandable)
- Abstract interface to manage provider switching
- AI provider selection per conversation
- Command-based provider switching (/provider command)
- API key management per user
- Configurable model parameters (temperature, tokens, etc.)

### Messaging Platform Integration
- Primary: Telegram bot integration
- Future: WhatsApp and other messaging platforms
- API/Terminal interface for testing and direct communication
- Message routing system between platforms and AI services

### External Messenger Commands
- Standard bot control commands:
  - `/start` - Initialize bot and display welcome message
  - `/help` - Show available commands and descriptions
  - `/clear` - Clear conversation history
- Character management commands:
  - `/character <id>` - Switch to a specific character
  - `/characters` - List all available characters
  - `/create_character` - Create a new character with custom properties
  - `/edit_character` - Edit an existing character's properties
  - `/delete_character <id>` - Delete a character
- AI Provider commands:
  - `/provider` - View or change the AI provider for the current conversation
- Module-specific commands:
  - `/remind` - Set a reminder
  - `/reminders` - List pending reminders
  - `/clear_reminders` - Clear all reminders
- Custom command registration system for modules
- Command permissions based on user role
- Command aliases for common operations

### Memory Management System
- Conversation history tracking
- Retrieval Augmented Generation (RAG) implementation:
  - Message vectorization using embeddings
  - Vector database storage (ChromaDB/FAISS)
  - Hybrid retrieval strategy combining:
    - Semantic relevance (vector similarity)
    - Temporal recency (recent messages)
    - User-defined importance (pinned content)
  - Dynamic context window construction
  - Automatic summarization of older conversations
- Smart token management:
  - Token counting and budget allocation
  - Context pruning based on relevance
  - Tiered storage (recent messages in full, older messages as summaries)
- User-specific memory persistence across sessions
- Memory isolation between users
- Storage strategy:
  - Initial: Railway volume for vector database (/data/vectordb)
  - Designed for future migration to dedicated vector database service if needed

### Configurable Character System
- Customizable bot personas (e.g., virtual girlfriend, lawyer, design consultant)
- Rule-based configuration for bot behavior
- System prompt generation based on character settings
- Default character for new users

### Augmented Context
- Integration with external knowledge sources:
  - Document upload (.md, .txt, etc.)
  - Notion integration (initial external service)
- Context items manageable through dashboard
- Assignment of context to specific modules or general use

### Module System
- Extensible features (shopping lists, task lists, etc.)
- Natural language triggers for module activation
- User-configurable module settings
- Dynamic module loading based on user configuration

### Web Dashboard
- User authentication (login/logout)
- Per-user configuration:
  - AI provider settings
  - Bot character customization
  - Module management
  - Memory settings
  - Messaging platform setup
- Admin user with default credentials

### Error Handling & Logging
- Clean, structured error messages focused on actionability
- Hierarchical logging system with configurable verbosity levels:
  - `ERROR`: Critical issues requiring immediate attention
  - `WARNING`: Potential issues that don't prevent operation
  - `INFO`: High-level system operations (default level)
  - `DEBUG`: Detailed information for troubleshooting
- Error codes with clear descriptions for quick identification
- Centralized error collection with context preservation
- User-friendly error responses (no stack traces in user-facing errors)
- Testing mode with enhanced logging for development
- Command-line options to adjust logging detail
- Regular log rotation to prevent storage issues
- Telegram admin channel for critical error notifications

### Security Considerations
- API request rate limiting to prevent abuse
- Hard limits on resource consumption:
  - Maximum token usage per conversation
  - Maximum vector database size per user
  - Maximum number of requests per time period
  - Automatic shutdown mechanisms for abnormal usage patterns
- API key security:
  - Encrypted storage for all user API keys
  - Access control to prevent key leakage
  - Regular validation of API key permissions
- Data isolation between users
- Input sanitization for all user-provided data
- CSRF protection for web dashboard
- Regular security scanning of dependencies
- Secure default configurations

### Language Support
- English UI for dashboard and system messages (initial version)
- Character language configurable through rules and settings
- Language-agnostic design patterns for future localization
- Unicode support throughout the system

### Simple Onboarding Experience
- Email-based registration with secure code verification
- Minimal required configuration to get started
- Guided setup for first-time users
- Default configurations for quick deployment
- Sample templates for common use cases

### Deployment
- Docker containerization
- Railway deployment
- Environment variable configuration
- Railway volume for persistent storage

### Environment Variables
- `TELEGRAM_BOT_TOKEN`: Token for Telegram bot API
- `OPENAI_API_KEY`: API key for OpenAI services
- `GROK_API_KEY`: API key for Grok AI services
- `VECTOR_DB_PATH`: Path to vector database storage (/data/vectordb)
- `RAILWAY_PROJECT_ID`: Railway project identifier
- `LOG_LEVEL`: Logging verbosity level (default: INFO)
- Additional variables for database connections (auto-injected by Railway)

### Modularity Principles
- Strict separation of concerns between all major systems
- Clean interfaces between components with well-defined APIs
- Independent development, testing, and deployment capabilities
- Ability to replace or upgrade individual components without affecting others
- Pluggable architecture allowing new integrations without core code changes
- Core components should be developed as separate packages/modules:
  - Message handling system
  - Memory management
  - Character/rules system
  - Module framework
  - AI provider integrations
  - Messaging platform adapters
  - Dashboard/admin interface

## System Architecture

### Overall Architecture

```
┌─────────────────────┐      ┌─────────────────────┐
│ Messaging Platforms │      │    AI Providers     │
│  ┌───────────────┐  │      │  ┌───────────────┐  │
│  │    Telegram   │  │      │  │    OpenAI     │  │
│  └───────────────┘  │      │  └───────────────┘  │
│  ┌───────────────┐  │      │  ┌───────────────┐  │
│  │   WhatsApp    │  │      │  │     Grok      │  │
│  └───────────────┘  │      │  └───────────────┘  │
│  ┌───────────────┐  │      │  ┌───────────────┐  │
│  │    Others     │  │      │  │   DeepSeek    │  │
│  └───────────────┘  │      │  └───────────────┘  │
└──────────┬──────────┘      └──────────┬──────────┘
           │                            │
           ▼                            ▼
┌──────────────────────────────────────────────────┐
│                   Core System                    │
│  ┌───────────────┐        ┌───────────────────┐  │
│  │ Message Router│◄──────►│  Memory Manager   │  │
│  └───────────────┘        └───────────────────┘  │
│  ┌───────────────┐        ┌───────────────────┐  │
│  │ User Manager  │◄──────►│ Context Processor │  │
│  └───────────────┘        └───────────────────┘  │
│  ┌───────────────┐        ┌───────────────────┐  │
│  │Module Manager │◄──────►│   Config Manager  │  │
│  └───────────────┘        └───────────────────┘  │
└──────────────────────────┬───────────────────────┘
                           │
                           ▼
               ┌──────────────────────┐
               │    Web Dashboard     │
               │  ┌────────────────┐  │
               │  │ User Settings  │  │
               │  └────────────────┘  │
               │  ┌────────────────┐  │
               │  │  Bot Config    │  │
               │  └────────────────┘  │
               │  ┌────────────────┐  │
               │  │Module Selection│  │
               │  └────────────────┘  │
               └──────────────────────┘
```

### RAG Memory System Architecture

```
┌─────────────────┐
│  User Message   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Message Vectorization │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│            Vector Database          │
│  ┌───────────┐  ┌───────────────┐   │
│  │ Recent    │  │ Historical    │   │
│  │ Messages  │  │ Conversations │   │
│  └───────────┘  └───────────────┘   │
└───────────────────┬─────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│         Context Construction        │
│  ┌───────────┐  ┌───────────────┐   │
│  │ Semantic  │  │   Recency     │   │
│  │ Relevance │  │   Weighting   │   │
│  └───────────┘  └───────────────┘   │
│  ┌───────────┐  ┌───────────────┐   │
│  │  Token    │  │  Importance   │   │
│  │  Budget   │  │   Markers     │   │
│  └───────────┘  └───────────────┘   │
└───────────────────┬─────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│            AI Request               │
│  ┌───────────┐  ┌───────────────┐   │
│  │  System   │  │  Retrieved    │   │
│  │  Prompt   │  │   Context     │   │
│  └───────────┘  └───────────────┘   │
│  ┌───────────────────────────────┐  │
│  │        User Query             │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

### Component Interaction Model

```
┌────────────────┐     ┌───────────────┐      ┌────────────────┐
│  User Request  │────▶│Message Adapter│─────▶│ Message Router │
└────────────────┘     └───────────────┘      └────────┬───────┘
                                                       │
                                                       ▼
┌────────────────┐     ┌───────────────┐      ┌────────────────┐
│   AI Response  │◀────│  AI Adapter   │◀─────│ Context Builder│
└────────────────┘     └───────────────┘      └────────┬───────┘
                                                       │
                                               ┌───────┴───────┐
                                               │               │
                                     ┌─────────▼─────┐ ┌───────▼────────┐
                                     │Memory Manager │ │Character Config│
                                     └───────────────┘ └────────────────┘
```

## Tech Stack

- **Backend Framework:** FastAPI (API + web dashboard)
- **Database:**
  - PostgreSQL (user data, configuration)
  - Vector DB (Chroma/FAISS for semantic memory)
- **AI Integration:** Custom provider adapters
- **Message Platforms:** Platform-specific client libraries
- **Deployment:** Docker + Railway
- **Authentication:** JWT tokens
- **Package Structure:** Independent packages for each major component
- **Embedding Models:** OpenAI Ada or open-source alternatives (SentenceTransformers)

## Core Components

### 1. Messaging Platform Adapters
Handles connection with external messaging platforms like Telegram. Responsible for:
- Receiving incoming messages
- Routing to core message system
- Sending responses back to users
- Developed as independent adapters that implement a common interface
- Command parsing and handling for platform-specific commands

### 2. AI Provider Adapters
Manages connections to different AI services. Responsible for:
- API authentication
- Request formatting
- Response parsing
- Error handling
- Developed as independent adapters that implement a common provider interface

### 3. Memory Management System
Hybrid storage system for conversation context. Features:
- Recent message storage
- Vector-based semantic retrieval
- External context integration
- Smart context windowing
- Completely isolated from other system components, accessed via a clean API
- RAG implementation details:
  - Embedding generation for all messages
  - Vector similarity search for context retrieval
  - Configurable retrieval strategies (semantic, temporal, hybrid)
  - Automatic conversation summarization for long-term storage
  - Token budget management to prevent context overflow

### 4. Character Management System
Manages bot personality and behavior rules. Includes:
- Character templates
- Custom rule sets
- System prompt generation
- Context integration
- Self-contained module with clear interfaces for configuration and prompt generation

### 5. Module System
Extensible functionality through modules. Provides:
- Task/Shopping list capabilities
- Natural language triggers
- User-specific configuration
- Dynamic module loading
- Plugin architecture for easy addition of new modules without core code changes
- Command registration interface for platform-specific commands

### 6. Message Router
Central component coordinating the system. Handles:
- Message processing pipeline
- Module invocation
- Context assembly
- AI request generation
- Acts as an orchestrator, with minimal business logic of its own
- Command routing to appropriate handlers

### 7. Web Dashboard
User interface for system configuration. Features:
- User authentication
- Bot configuration
- Module management
- API key settings
- Memory configuration
- Completely decoupled from core bot functionality, communicating only through APIs

## Database Schema

```sql
-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User profiles
CREATE TABLE user_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    name VARCHAR(255),
    preferences JSONB DEFAULT '{}'
);

-- AI provider configurations
CREATE TABLE ai_providers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    provider_type VARCHAR(50) NOT NULL, -- openai, grok, deepseek, etc.
    api_key VARCHAR(255),
    is_default BOOLEAN DEFAULT false,
    config JSONB DEFAULT '{}'
);

-- Character configurations
CREATE TABLE characters (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    personality TEXT,
    rules JSONB,
    context_ids JSONB, -- References to context items
    is_active BOOLEAN DEFAULT false
);

-- Messaging platform connections
CREATE TABLE platform_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    platform_type VARCHAR(50) NOT NULL, -- telegram, whatsapp, etc.
    credentials JSONB,
    is_active BOOLEAN DEFAULT false
);

-- Message history
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    conversation_id VARCHAR(255),
    role VARCHAR(50) NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    platform VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding_id VARCHAR(255) -- Reference to vector embedding
);

-- Message embeddings (for vector search)
CREATE TABLE message_embeddings (
    id VARCHAR(255) PRIMARY KEY,
    message_id INTEGER REFERENCES messages(id),
    collection VARCHAR(50) NOT NULL, -- Vector DB collection name
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversation summaries
CREATE TABLE conversation_summaries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    start_message_id INTEGER REFERENCES messages(id),
    end_message_id INTEGER REFERENCES messages(id),
    summary TEXT NOT NULL,
    embedding_id VARCHAR(255), -- Reference to vector embedding
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Context items (external documents, notes)
CREATE TABLE context_items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    content TEXT,
    source_type VARCHAR(50), -- notion, file, etc.
    source_id VARCHAR(255),
    embedding_id VARCHAR(255), -- Reference to vector embedding
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User modules
CREATE TABLE modules (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    type VARCHAR(50) NOT NULL, -- shopping_list, task_list, etc.
    name VARCHAR(255) NOT NULL,
    config JSONB DEFAULT '{}',
    enabled BOOLEAN DEFAULT true
);

-- Commands
CREATE TABLE commands (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    module_id INTEGER REFERENCES modules(id),
    handler_path VARCHAR(255) NOT NULL, -- Path to command handler
    is_system BOOLEAN DEFAULT false, -- System commands vs module commands
    enabled BOOLEAN DEFAULT true
);

-- System logs
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) NOT NULL, -- ERROR, WARNING, INFO, DEBUG
    component VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Implementation Plan

### Phase 1: Core Infrastructure and Modularity Setup
- Project structure setup with modular architecture
- Define clean interfaces between components
- Set up core message routing with pluggable adapter interfaces
- Basic Telegram integration with command handling
- Simple memory system with RAG foundation
- Implement essential bot commands
- Error handling and logging infrastructure

### Phase 2: Memory & Character System
- Database schema implementation
- Vector storage for semantic search
- Character configuration system
- Basic module system
- Enhance RAG implementation with better retrieval strategies

### Phase 3: Web Dashboard
- User authentication
- Configuration interface
- API key management
- Module management
- Memory visualization and management

### Phase 4: Deployment & Scaling
- Docker configuration
- Railway setup
- Environment variable management
- Performance optimization
- RAG optimization for larger conversation histories

## Development Priorities

### MVP Core Functionality
1. Messaging integration (Telegram)
2. Basic AI provider integration (OpenAI)
3. Simple memory system with basic RAG
4. Essential character configuration
5. Basic error handling

### Secondary Features
1. Web dashboard
2. Additional AI providers
3. Advanced RAG features
4. Module system
5. Notion integration

### Extended Features
1. Additional messaging platforms
2. Advanced analytics
3. Performance optimizations
4. Additional external integrations

## Performance Considerations
- Start with simplicity, focus on functionality over optimization
- Identify potential bottlenecks early:
  - Vector database operations
  - Large context handling
  - AI API request latency
- Implement basic monitoring from the beginning
- Decouple components to allow independent scaling
- Use asynchronous processing where appropriate
- Consider background tasks for non-critical operations
- Implement caching for frequently accessed data

## Documentation Standards
- Comprehensive docstrings for all public functions, classes, and methods
- README files for each module explaining purpose and usage
- API documentation with example requests/responses
- Clear inline comments explaining complex logic or decisions
- Architecture diagrams for major components
- Development guidelines for contributors
- Avoid over-documenting simple code
- Document architectural decisions and the reasoning behind them
- Keep documentation close to the code it describes
- Version documentation alongside code

## Project Structure

```
brainy/
├── core/                      # Core system components
│   ├── message_router/        # Central message routing system
│   ├── memory_manager/        # Memory and context management
│   │   ├── vector_store/      # RAG implementation
│   │   ├── embeddings/        # Embedding generation
│   │   └── context_builder/   # Context window construction
│   ├── character_manager/     # Character/rules configuration
│   └── module_framework/      # Framework for module plugins
├── adapters/                  # Pluggable adapter interfaces
│   ├── messaging/             # Messaging platform adapters
│   │   ├── telegram/          # Telegram integration
│   │   │   └── commands/      # Telegram commands
│   │   └── whatsapp/          # WhatsApp integration (future)
│   └── ai_providers/          # AI service adapters
│       ├── openai/            # OpenAI integration
│       ├── grok/              # Grok integration
│       └── deepseek/          # DeepSeek integration
├── modules/                   # Extension modules
│   ├── shopping_list/         # Shopping list functionality
│   ├── task_manager/          # Task management
│   └── context_augmenters/    # Context enhancement modules
├── dashboard/                 # Web dashboard
│   ├── frontend/              # UI components
│   └── api/                   # Dashboard API endpoints
├── database/                  # Database models and migrations
├── config/                    # Configuration management
├── utils/                     # Shared utilities and helpers
│   ├── error_handling/        # Error handling utilities
│   ├── logging/               # Logging configuration
│   └── security/              # Security utilities
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── fixtures/              # Test fixtures
└── docs/                      # Documentation
    ├── architecture/          # Architecture documentation
    ├── api/                   # API documentation
    └── development/           # Development guidelines
```
