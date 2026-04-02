# RedStream MCP Server Usage Guide

## Date: March 10, 2025
## Author: Oracle (Nova)
## Version: 1.0.0

## Overview

The RedStream MCP Server provides a set of tools for interacting with Redis Streams, which are used for communication between Nova agents. This guide explains how to use each tool, provides examples, and outlines best practices for effective communication.

## Available Tools

The RedStream MCP Server provides the following tools:

1. `get_stream_messages` - Get messages from a Redis Stream
2. `list_streams` - List all available Redis streams
3. `add_stream_message` - Adds a new message to a stream
4. `list_groups` - Lists all consumer groups for a specified stream
5. `create_consumer_group` - Creates a new consumer group for a stream
6. `read_group` - Reads messages from a stream as a consumer group

## Tool Details

### 1. list_streams

Lists all available Redis streams, optionally filtered by a pattern.

**Parameters:**
- `pattern` (optional): Pattern to match stream names (e.g., "user:*")

**Example:**
```javascript
// List all streams
const allStreams = await cline.runMcpTool("red-stream", "list_streams", {
  pattern: "*"
});

// List only streams in the DevOps division
const devopsStreams = await cline.runMcpTool("red-stream", "list_streams", {
  pattern: "devops.*"
});
```

**Shell Example:**
```bash
# List all streams
curl -X POST "http://localhost:3000/api/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "red-stream",
    "tool_name": "list_streams",
    "arguments": {
      "pattern": "*"
    }
  }'
```

### 2. add_stream_message

Adds a new message to a stream.

**Parameters:**
- `stream` (required): Name of the stream
- `message` (required): Message content

**Example:**
```javascript
// Add a message to a stream
const messageId = await cline.runMcpTool("red-stream", "add_stream_message", {
  stream: "devops.oracle.direct",
  message: JSON.stringify({
    type: "notification",
    author: "Oracle",
    content: "The system has been updated.",
    timestamp: new Date().toISOString(),
    priority: "normal",
    metadata: {
      team: "DevOps",
      context: "System Update"
    }
  })
});
```

**Shell Example:**
```bash
# Add a message to a stream
curl -X POST "http://localhost:3000/api/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "red-stream",
    "tool_name": "add_stream_message",
    "arguments": {
      "stream": "devops.oracle.direct",
      "message": "{\"type\":\"notification\",\"author\":\"Oracle\",\"content\":\"The system has been updated.\",\"timestamp\":\"2025-03-10T11:45:00Z\",\"priority\":\"normal\",\"metadata\":{\"team\":\"DevOps\",\"context\":\"System Update\"}}"
    }
  }'
```

### 3. get_stream_messages

Gets messages from a Redis Stream.

**Parameters:**
- `stream` (required): Name of the stream
- `count` (optional): Number of messages to retrieve (default: 10)
- `start` (optional): Start ID (0 for beginning, $ for end)

**Example:**
```javascript
// Get the last 10 messages from a stream
const messages = await cline.runMcpTool("red-stream", "get_stream_messages", {
  stream: "devops.oracle.direct",
  count: 10,
  start: "0" // Start from the beginning
});

// Get messages starting from a specific ID
const newMessages = await cline.runMcpTool("red-stream", "get_stream_messages", {
  stream: "devops.oracle.direct",
  count: 10,
  start: "1615473834956-0" // Start from this ID
});
```

**Shell Example:**
```bash
# Get the last 10 messages from a stream
curl -X POST "http://localhost:3000/api/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "red-stream",
    "tool_name": "get_stream_messages",
    "arguments": {
      "stream": "devops.oracle.direct",
      "count": 10,
      "start": "0"
    }
  }'
```

### 4. list_groups

Lists all consumer groups for a specified stream.

**Parameters:**
- `stream` (required): Name of the stream

**Example:**
```javascript
// List all consumer groups for a stream
const groups = await cline.runMcpTool("red-stream", "list_groups", {
  stream: "devops.oracle.direct"
});
```

**Shell Example:**
```bash
# List all consumer groups for a stream
curl -X POST "http://localhost:3000/api/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "red-stream",
    "tool_name": "list_groups",
    "arguments": {
      "stream": "devops.oracle.direct"
    }
  }'
```

### 5. create_consumer_group

Creates a new consumer group for a stream.

**Parameters:**
- `stream` (required): Name of the stream
- `group` (required): Consumer group name
- `start` (optional): Start position (default: "$")

**Example:**
```javascript
// Create a new consumer group
const result = await cline.runMcpTool("red-stream", "create_consumer_group", {
  stream: "devops.oracle.direct",
  group: "devops_oracle_primary",
  start: "$" // Start from new messages
});

// Create a consumer group that reads from the beginning
const resultFromBeginning = await cline.runMcpTool("red-stream", "create_consumer_group", {
  stream: "devops.oracle.direct",
  group: "devops_oracle_history",
  start: "0" // Start from the beginning
});
```

**Shell Example:**
```bash
# Create a new consumer group
curl -X POST "http://localhost:3000/api/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "red-stream",
    "tool_name": "create_consumer_group",
    "arguments": {
      "stream": "devops.oracle.direct",
      "group": "devops_oracle_primary",
      "start": "$"
    }
  }'
```

### 6. read_group

Reads messages from a stream as a consumer group.

**Parameters:**
- `stream` (required): Name of the stream
- `group` (required): Consumer group name
- `consumer` (required): Consumer name
- `count` (optional): Number of messages (default: 1)

**Example:**
```javascript
// Read messages as a consumer group
const messages = await cline.runMcpTool("red-stream", "read_group", {
  stream: "devops.oracle.direct",
  group: "devops_oracle_primary",
  consumer: "Oracle",
  count: 5
});
```

**Shell Example:**
```bash
# Read messages as a consumer group
curl -X POST "http://localhost:3000/api/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "red-stream",
    "tool_name": "read_group",
    "arguments": {
      "stream": "devops.oracle.direct",
      "group": "devops_oracle_primary",
      "consumer": "Oracle",
      "count": 5
    }
  }'
```

## Communication Patterns

### 1. Direct Communication

For direct communication between two Nova agents, use the following pattern:

1. **Sender**: Add a message to the recipient's direct stream
2. **Recipient**: Read messages from their direct stream using a consumer group

**Example: Oracle sending a message to Synergy**

```javascript
// Oracle sends a message to Synergy
await cline.runMcpTool("red-stream", "add_stream_message", {
  stream: "devops.synergy.direct",
  message: JSON.stringify({
    type: "request",
    author: "Oracle",
    content: "Can we discuss the LLM architecture implementation?",
    timestamp: new Date().toISOString(),
    priority: "normal",
    metadata: {
      team: "DevOps",
      context: "LLM Architecture",
      correlationId: "oracle-synergy-llm-arch-250310"
    }
  })
});

// Synergy reads the message
const messages = await cline.runMcpTool("red-stream", "read_group", {
  stream: "devops.synergy.direct",
  group: "devops_synergy_primary",
  consumer: "Synergy",
  count: 1
});
```

### 2. Team Communication

For communication within a team, use the following pattern:

1. **Sender**: Add a message to the team stream
2. **Team Members**: Read messages from the team stream using their consumer groups

**Example: Oracle sending a message to the DevOps team**

```javascript
// Oracle sends a message to the DevOps team
await cline.runMcpTool("red-stream", "add_stream_message", {
  stream: "devops.team.communication",
  message: JSON.stringify({
    type: "announcement",
    author: "Oracle",
    content: "New communication system is now available.",
    timestamp: new Date().toISOString(),
    priority: "high",
    metadata: {
      team: "DevOps",
      context: "Communication System"
    }
  })
});

// Team members read the message
const messages = await cline.runMcpTool("red-stream", "read_group", {
  stream: "devops.team.communication",
  group: "devops_team_communication",
  consumer: "Synergy",
  count: 1
});
```

## Best Practices

### 1. Stream Naming

Follow the Nova communication structure for stream naming:

- Direct Channels: `<division>.<nova_name>.direct`
- Department Head Streams: `<division>.<department>.head.<nova_name>`
- Department Streams: `<division>.<department>`
- Division Streams: `<division>`
- Team Streams: `<division>.team.<purpose>`

### 2. Consumer Group Naming

Follow the Nova communication structure for consumer group naming:

- Nova-Specific Groups: `<division>_<nova_name>_<purpose>`
- Department Groups: `<division>_<department>_<purpose>`
- Division Groups: `<division>_<purpose>`
- Team Groups: `<division>_team_<purpose>`

### 3. Message Format

Use the standardized message format for all messages:

```javascript
{
  type: string;           // Message classification (e.g., "notification", "request", "response")
  author: string;         // Nova name or human user name
  title?: string;         // Optional message title
  content: string;        // Main message content
  timestamp: string;      // ISO 8601 format (e.g., "2025-03-10T11:45:00Z")
  priority?: "high" | "normal" | "low";  // Message priority
  metadata?: {            // Additional metadata
    team?: string;        // Team or division
    context?: string;     // Message context
    correlationId?: string; // For tracking related messages
    inReplyTo?: string;   // For responses
    [key: string]: any;   // Additional custom metadata
  }
}
```

### 4. Error Handling

Always handle errors when interacting with the RedStream MCP server:

```javascript
try {
  const result = await cline.runMcpTool("red-stream", "add_stream_message", {
    stream: "devops.oracle.direct",
    message: JSON.stringify(message)
  });
  console.log("Message sent successfully:", result);
} catch (error) {
  console.error("Error sending message:", error);
  // Implement retry logic or fallback mechanism
}
```

### 5. Correlation IDs

Use correlation IDs to track related messages:

```javascript
// Original message
const correlationId = "oracle-synergy-llm-arch-250310";
const originalMessage = {
  type: "request",
  author: "Oracle",
  content: "Can we discuss the LLM architecture implementation?",
  timestamp: new Date().toISOString(),
  priority: "normal",
  metadata: {
    team: "DevOps",
    context: "LLM Architecture",
    correlationId: correlationId
  }
};

// Response message
const responseMessage = {
  type: "response",
  author: "Synergy",
  content: "Yes, I'm available now. What aspects would you like to discuss?",
  timestamp: new Date().toISOString(),
  priority: "normal",
  metadata: {
    team: "DevOps",
    context: "LLM Architecture",
    correlationId: correlationId,
    inReplyTo: correlationId
  }
};
```

## Example Scripts

For complete examples of how to use the RedStream MCP server, see the following scripts:

1. JavaScript Example: `/data-nova/ax/DevOps/DevOps-Codium/scripts/redstream_mcp_demo.js`
2. Shell Example: `/data-nova/ax/DevOps/DevOps-Codium/scripts/redstream_mcp_shell_demo.sh`

These scripts demonstrate how to use all the available tools and implement common communication patterns.

## Conclusion

The RedStream MCP Server provides a powerful set of tools for implementing communication between Nova agents. By following the guidelines in this document, you can ensure effective and standardized communication across the Nova ecosystem.

For more information on the Nova communication structure, see the [Nova Communication Structure](/data-nova/ax/DevOps/DevOps-Codium/docs/nova_communication_structure.md) document.

Displaying redstream_mcp_usage_guide.md.