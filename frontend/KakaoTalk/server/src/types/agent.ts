/**
 * Kanana DualGuard Agent Types
 * FastAPI Agent API와의 통신을 위한 타입 정의
 */

export enum RiskLevel {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL'
}

export interface SecurityAnalysis {
  risk_level: RiskLevel;
  reasons: string[];
  recommended_action: string;
  is_secret_recommended?: boolean;
}

export interface OutgoingAnalysisRequest {
  text: string;
  sender_id?: number;
  receiver_id?: number;
  use_ai?: boolean;  // Kanana LLM 사용 여부
}

export interface IncomingAnalysisRequest {
  text: string;
  sender_id?: number;
  receiver_id?: number;
  use_ai?: boolean;  // Kanana LLM 사용 여부
}

export interface AgentApiResponse {
  risk_level: string;
  reasons: string[];
  recommended_action: string;
  is_secret_recommended: boolean;
}
