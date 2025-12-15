# URL Safety Tools Implementation Plan

## Goal
Add URL verification capabilities to the existing MCP server using Google Safe Browsing and VirusTotal APIs.

## New Tools

### 1. `check_google_safe_browsing`
*   **Source**: Google Safe Browsing API v4.
*   **Input**: `url` (string).
*   **Requirement**: `GOOGLE_API_KEY` environment variable.
*   **Logic**: Sends a POST request to `threatMatches:find`. Returns "Safe" or the threat type (e.g., "SOCIAL_ENGINEERING").

### 2. `check_virustotal`
*   **Source**: VirusTotal API v2 (simpler for URL reports) or v3.
*   **Input**: `url` (string).
*   **Requirement**: `VIRUSTOTAL_API_KEY` environment variable.
*   **Logic**: Sends a GET request to `url/report`. Returns the scan ratio (e.g., "5/90 engines detected this").

## Changes
*   **File**: `fraud_mcp_server.py`
    *   Import `os`.
    *   Add the new functions decorated with `@mcp.tool()`.
    *   Add helper logic to check for API keys and return helpful error messages if missing.
*   **File**: `README_MCP.md`
    *   Add sections for "URL Safety Tools".
    *   Add "Configuration" section explaining how to get API keys.

## Verification
*   Since I don't have keys, I will verify the code structure and error handling (missing key message).
