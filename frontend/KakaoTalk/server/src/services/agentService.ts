/**
 * Kanana DualGuard Agent Service
 * FastAPI Agent API와 통신하는 서비스 레이어
 *
 * 모듈화: Agent API 호출 로직을 캡슐화
 * 멀티에이전트: Outgoing Agent와 Incoming Agent를 독립적으로 호출
 */

import axios from 'axios';
import logger from '../logger';
import {
  SecurityAnalysis,
  OutgoingAnalysisRequest,
  IncomingAnalysisRequest,
  AgentApiResponse,
  RiskLevel
} from '../types/agent';

// FastAPI Agent API 베이스 URL
const AGENT_API_BASE_URL = process.env.AGENT_API_URL || 'http://localhost:8002/api/agents';

/**
 * 안심 전송 Agent (Outgoing) - 발신 메시지 분석
 * 민감정보를 감지하고 시크릿 전송을 추천합니다.
 */
export const analyzeOutgoing = async (
  text: string,
  sender_id?: number,
  receiver_id?: number
): Promise<SecurityAnalysis | null> => {
  try {
    const request: OutgoingAnalysisRequest = {
      text,
      sender_id,
      receiver_id,
      use_ai: true  // Kanana LLM 분석 활성화
    };

    const response = await axios.post<AgentApiResponse>(
      `${AGENT_API_BASE_URL}/analyze/outgoing`,
      request,
      {
        timeout: 30000, // LLM 호출 고려 30초 타임아웃
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );

    const result: SecurityAnalysis = {
      risk_level: response.data.risk_level as RiskLevel,
      reasons: response.data.reasons,
      recommended_action: response.data.recommended_action,
      is_secret_recommended: response.data.is_secret_recommended
    };

    logger.info(`Outgoing Agent Analysis: ${result.risk_level} - ${text.substring(0, 50)}`);
    return result;

  } catch (error) {
    logger.error(`Outgoing Agent API Error: ${error}`);
    // Agent API 실패 시 null 반환 (채팅은 계속 진행)
    return null;
  }
};

/**
 * 대화 히스토리 타입 정의
 */
interface ConversationMessage {
  sender_id: number;
  message: string;
  timestamp: Date;
}

/**
 * 안심 가드 Agent (Incoming) - 수신 메시지 분석
 * 피싱, 사기, 가족 사칭 등을 감지합니다.
 *
 * v2.0: 대화 히스토리 기반 맥락 분석 지원
 * - conversation_history: 최근 대화 목록 (시간순)
 * - Agent B가 대화 흐름을 분석하여 사기 "가능성"을 판단
 */
export const analyzeIncoming = async (
  text: string,
  sender_id?: number,
  receiver_id?: number,
  conversation_history?: ConversationMessage[]
): Promise<SecurityAnalysis | null> => {
  try {
    const request = {
      text,
      sender_id,
      receiver_id,
      conversation_history: conversation_history || [],  // 대화 맥락 전달
      use_ai: true  // Kanana LLM 활성화
    };

    const response = await axios.post<AgentApiResponse>(
      `${AGENT_API_BASE_URL}/analyze/incoming`,
      request,
      {
        timeout: 30000, // LLM 호출 고려 30초 타임아웃
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );

    const result: SecurityAnalysis = {
      risk_level: response.data.risk_level as RiskLevel,
      reasons: response.data.reasons,
      recommended_action: response.data.recommended_action,
      is_secret_recommended: false
    };

    logger.info(`Incoming Agent Analysis: ${result.risk_level} - ${text.substring(0, 50)} (history: ${conversation_history?.length || 0} msgs)`);
    return result;

  } catch (error) {
    logger.error(`Incoming Agent API Error: ${error}`);
    return null;
  }
};

/**
 * 이미지 분석 Agent - 이미지 내 민감정보 감지
 * Vision OCR로 텍스트 추출 후 PII 분석
 */
export const analyzeImage = async (
  imageBuffer: Buffer,
  filename: string
): Promise<SecurityAnalysis | null> => {
  try {
    const FormData = require('form-data');
    const formData = new FormData();
    formData.append('file', imageBuffer, {
      filename: filename,
      contentType: 'image/png'
    });

    const response = await axios.post<AgentApiResponse>(
      `${AGENT_API_BASE_URL}/analyze/image`,
      formData,
      {
        timeout: 60000, // Vision + Instruct 모델 로드 시간 고려 60초
        headers: {
          ...formData.getHeaders()
        }
      }
    );

    const result: SecurityAnalysis = {
      risk_level: response.data.risk_level as RiskLevel,
      reasons: response.data.reasons,
      recommended_action: response.data.recommended_action,
      is_secret_recommended: response.data.is_secret_recommended
    };

    logger.info(`Image Agent Analysis: ${result.risk_level} - ${filename}`);
    return result;

  } catch (error) {
    logger.error(`Image Agent API Error: ${error}`);
    return null;
  }
};

/**
 * Agent API 헬스체크
 */
export const checkAgentHealth = async (): Promise<boolean> => {
  try {
    const response = await axios.get(`${AGENT_API_BASE_URL}/health`, {
      timeout: 3000
    });
    return response.status === 200;
  } catch (error) {
    logger.error(`Agent API Health Check Failed: ${error}`);
    return false;
  }
};
