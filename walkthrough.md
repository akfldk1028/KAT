# Kanana DualGuard Verification & Setup Walkthrough

## 1. Project Status Overview
I have verified and started the full stack environment for Kanana DualGuard.
- **Backend**: Python FastAPI server is running on **Port 8002**.
- **Node.js Server**: Middleware/API server is running on **Port 8001**.
- **Frontend**: React Client is running on **Port 3000**.

## 2. Fixes Applied
1.  **Backend Fixes**:
    - Implemented missing `AgentManager` in `agent/agent_manager.py`.
    - Fixed import errors in `test_agents.py`, `security.py`, and `agents.py`.
    - Changed Backend port to `8002` to avoid conflicts.
2.  **Frontend Configuration**:
    - Updated `frontend/KakaoTalk/server/src/services/agentService.ts` to connect to Backend on port `8002`.
    - Fixed React Client startup on Node.js v22 using `--openssl-legacy-provider`.

## 3. How to Test (Single User)
1.  **Frontend**: Go to `http://localhost:3000`.
2.  **Login/Signup**: Create an account.
3.  **Test Scenarios**:
    - **Outgoing**: Send `123-45-67890` to see "Secret Send" recommendation.

## 4. How to Test Chat (Multi-User Simulation)
To test real-time chatting between two users on one computer:

1.  **User A (Window 1)**:
    - Open Chrome (or your browser) and go to `http://localhost:3000`.
    - Sign up/Login as **User A** (e.g., `user1`).

2.  **User B (Window 2)**:
    - Open an **Incognito Window** (Secret Mode, `Ctrl+Shift+N`).
    - Go to `http://localhost:3000`.
    - Sign up/Login as **User B** (e.g., `user2`).

3.  **Connect & Chat**:
    - In Window 1 (User A), go to "Friends" tab -> "Add Friend".
    - Search for **User B** and add them.
    - Click on User B's profile and start a chat.
    - Type a message in Window 1. It should appear **instantly** in Window 2 without refreshing.

## 5. Technical Details
- **Backend**: `http://localhost:8002` (Swagger UI: `http://localhost:8002/docs`)
- **Node Server**: `http://localhost:8001`
- **Client**: `http://localhost:3000`

## 6. Note on Provided Key
The key `4dSPllwYFiVUpfNHCJPmZRz3PAi2qUk7nwaU9pmbj5MawW1m#ISkKZ68HoO5lrhoUEnxvnN7KYTmWjbPvXuEHFkYv1GE` is not currently used in the active code paths but is noted for future "Secret Send" encryption implementation.
