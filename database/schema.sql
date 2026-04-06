-- ============================================================
-- Agentic Chatbot Database Schema
-- MySQL Workbench Compatible
-- ============================================================

CREATE DATABASE IF NOT EXISTS chatbot_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE chatbot_db;

-- ============================================================
-- 1. CONVERSATIONS TABLE
--    Each row = one chat thread
-- ============================================================
CREATE TABLE IF NOT EXISTS conversations (
    id              VARCHAR(36)     PRIMARY KEY,
    title           VARCHAR(255)    NOT NULL DEFAULT 'New Chat',
    llm_provider    VARCHAR(50)     NOT NULL DEFAULT 'openai',
    llm_model       VARCHAR(100)    NOT NULL DEFAULT 'gpt-4o',
    tool_mode       VARCHAR(20)     NOT NULL DEFAULT 'auto',
    system_prompt   TEXT            DEFAULT NULL,
    is_archived     TINYINT(1)      NOT NULL DEFAULT 0,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_created   (created_at),
    INDEX idx_archived  (is_archived)
) ENGINE=InnoDB;

-- ============================================================
-- 2. MESSAGES TABLE
--    Stores every message in a conversation
-- ============================================================
CREATE TABLE IF NOT EXISTS messages (
    id                  INT             AUTO_INCREMENT PRIMARY KEY,
    conversation_id     VARCHAR(36)     NOT NULL,
    role                ENUM('user','assistant','system','tool')  NOT NULL,
    content             TEXT            NOT NULL,
    token_count         INT             NOT NULL DEFAULT 0,
    is_summarized       TINYINT(1)      NOT NULL DEFAULT 0,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (conversation_id)
        REFERENCES conversations(id) ON DELETE CASCADE,

    INDEX idx_conv_id        (conversation_id),
    INDEX idx_role            (role),
    INDEX idx_created_at      (created_at),
    INDEX idx_summarized      (is_summarized)
) ENGINE=InnoDB;

-- ============================================================
-- 3. CONVERSATION SUMMARIES TABLE
--    Compressed summaries for long conversations
-- ============================================================
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id                  INT             AUTO_INCREMENT PRIMARY KEY,
    conversation_id     VARCHAR(36)     NOT NULL,
    summary             TEXT            NOT NULL,
    summarized_up_to    INT             NOT NULL DEFAULT 0
        COMMENT 'message.id of the last message included in this summary',
    message_count       INT             NOT NULL DEFAULT 0,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (conversation_id)
        REFERENCES conversations(id) ON DELETE CASCADE,

    UNIQUE INDEX idx_conv_summary (conversation_id)
) ENGINE=InnoDB;

-- ============================================================
-- 4. TOOL CALLS TABLE
--    Logs every tool invocation for auditing
-- ============================================================
CREATE TABLE IF NOT EXISTS tool_calls (
    id                  INT             AUTO_INCREMENT PRIMARY KEY,
    message_id          INT             DEFAULT NULL,
    conversation_id     VARCHAR(36)     NOT NULL,
    tool_name           VARCHAR(100)    NOT NULL,
    tool_input          TEXT            DEFAULT NULL,
    tool_output         TEXT            DEFAULT NULL,
    execution_time_ms   INT             NOT NULL DEFAULT 0,
    status              ENUM('success','error','timeout') NOT NULL DEFAULT 'success',
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (message_id)
        REFERENCES messages(id) ON DELETE SET NULL,
    FOREIGN KEY (conversation_id)
        REFERENCES conversations(id) ON DELETE CASCADE,

    INDEX idx_tool_conv  (conversation_id),
    INDEX idx_tool_name  (tool_name)
) ENGINE=InnoDB;

-- ============================================================
-- 5. AGENT LOGS TABLE
--    Audit trail for every agent/node execution
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_logs (
    id                  INT             AUTO_INCREMENT PRIMARY KEY,
    conversation_id     VARCHAR(36)     NOT NULL,
    message_id          INT             DEFAULT NULL,
    agent_type          VARCHAR(50)     NOT NULL
        COMMENT 'orchestrator | chat | crag | blog | travel | academic | aggregator | memory | summarizer',
    node_name           VARCHAR(100)    DEFAULT NULL,
    input_summary       TEXT            DEFAULT NULL,
    output_summary      TEXT            DEFAULT NULL,
    execution_time_ms   INT             NOT NULL DEFAULT 0,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (conversation_id)
        REFERENCES conversations(id) ON DELETE CASCADE,

    INDEX idx_agent_conv     (conversation_id),
    INDEX idx_agent_type     (agent_type)
) ENGINE=InnoDB;

-- ============================================================
-- 6. USER PREFERENCES TABLE
--    Stores user-level settings (future expansion)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_preferences (
    id                  INT             AUTO_INCREMENT PRIMARY KEY,
    user_name           VARCHAR(100)    NOT NULL DEFAULT 'default',
    preferred_provider  VARCHAR(50)     NOT NULL DEFAULT 'openai',
    preferred_model     VARCHAR(100)    NOT NULL DEFAULT 'gpt-4o',
    preferred_tool_mode VARCHAR(20)     NOT NULL DEFAULT 'auto',
    theme               VARCHAR(20)     NOT NULL DEFAULT 'dark',
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE INDEX idx_user_name (user_name)
) ENGINE=InnoDB;

-- ============================================================
-- Insert default user preferences
-- ============================================================
INSERT IGNORE INTO user_preferences (user_name, preferred_provider, preferred_model, preferred_tool_mode, theme)
VALUES ('default', 'openai', 'gpt-4o', 'auto', 'dark');

-- ============================================================
-- 7. UPLOADED FILES TABLE
--    Tracks documents uploaded for RAG system
-- ============================================================
CREATE TABLE IF NOT EXISTS uploaded_files (
    id                  INT             AUTO_INCREMENT PRIMARY KEY,
    file_name           VARCHAR(255)    NOT NULL,
    file_path           VARCHAR(500)    NOT NULL,
    file_size           INT             NOT NULL DEFAULT 0,
    uploaded_at         TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE INDEX idx_file_name (file_name)
) ENGINE=InnoDB;
