export enum PAGE_PATHS {
  HOME = '/',
  LOGIN = '/login',
  SIGNUP = '/signup',
  MENU = '/menu',
  FRIENDS = '/menu/friends',
  CHATTING = '/menu/chatting',
  CHATTING_ROOM = '/room'
}

export const HOST = process.env.HOST || 'http://localhost:8001';

export const API_HOST = process.env.API_HOST || HOST + '/api';

// Agent API 서버 (포트 8004)
export const AGENT_HOST = process.env.AGENT_HOST || 'http://localhost:8004/api/agents';

// Secret Message API (Agent 서버 포트 8004에 통합)
export const SECRET_HOST = process.env.SECRET_HOST || 'http://localhost:8004/api/secret';

export const BASE_IMG_URL = '/asset/base_profile.jpg';
