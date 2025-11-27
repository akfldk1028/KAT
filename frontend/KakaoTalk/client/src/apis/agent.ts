/**
 * DualGuard Agent API
 * 이미지/메시지 보안 분석 API
 */
import axios from 'axios';
import { AGENT_HOST } from '~/constants';

export interface SecurityAnalysis {
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  reasons: string[];
  recommended_action: string;
  is_secret_recommended: boolean;
}

interface OCRResponse {
  extracted_text: string;
  cached: boolean;
}

/**
 * 이미지 분석 API (전체 Flow)
 * Vision OCR로 텍스트 추출 후 민감정보 분석
 *
 * @param imageFile 분석할 이미지 파일
 * @param useAi LLM 사용 여부 (기본: false = rule-based)
 */
export const analyzeImage = async (
  imageFile: File,
  useAi: boolean = false
): Promise<SecurityAnalysis> => {
  const formData = new FormData();
  formData.append('file', imageFile);

  const response = await axios.post<SecurityAnalysis>(
    `${AGENT_HOST}/analyze/image?use_ai=${useAi}`,
    formData,
    {
      timeout: 60000, // Vision 모델 로드 시간 고려
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }
  );

  return response.data;
};

/**
 * 이미지 OCR API (텍스트 추출만)
 * 이미지 선택 시점에 미리 호출하여 캐싱
 *
 * @param imageUrl 이미지 URL 또는 로컬 경로
 */
export const extractTextFromImage = async (imageUrl: string): Promise<OCRResponse> => {
  const response = await axios.post<OCRResponse>(
    `${AGENT_HOST}/ocr`,
    { image_url: imageUrl },
    { timeout: 30000 }
  );

  return response.data;
};

/**
 * 추출된 텍스트 분석 API
 * OCR 후 빠른 분석을 위해 사용
 *
 * @param extractedText OCR로 추출된 텍스트
 * @param useAi LLM 사용 여부
 */
export const analyzeTextFromImage = async (
  extractedText: string,
  useAi: boolean = true
): Promise<SecurityAnalysis> => {
  const response = await axios.post<SecurityAnalysis>(
    `${AGENT_HOST}/analyze/text-from-image`,
    { extracted_text: extractedText, use_ai: useAi },
    { timeout: 10000 }
  );

  return response.data;
};

/**
 * 발신 메시지 분석 API (안심 전송)
 * 민감정보 감지 (계좌번호, 주민번호 등)
 *
 * 2-Tier 분석:
 * - Tier 1: 빠른 필터링 (~0ms)
 * - Tier 2: LLM 정밀 분석 (use_ai=true, ~1-3초)
 *
 * @param text 분석할 메시지
 * @param useAi LLM 사용 여부 (기본: false = rule-based)
 */
export const analyzeOutgoing = async (
  text: string,
  useAi: boolean = false
): Promise<SecurityAnalysis> => {
  const response = await axios.post<SecurityAnalysis>(
    `${AGENT_HOST}/analyze/outgoing`,
    { text, use_ai: useAi },
    { timeout: 180000 }  // LLM 분석 시 ~60초 + 여유 시간 (3분)
  );

  return response.data;
};

/**
 * 수신 메시지 분석 API (안심 가드)
 * 피싱/사기/가족사칭 감지
 *
 * @param text 분석할 메시지
 * @param senderId 발신자 ID
 * @param useAi Kanana Safeguard AI 사용 여부
 */
export const analyzeIncoming = async (
  text: string,
  senderId?: number,
  useAi: boolean = false
): Promise<SecurityAnalysis> => {
  const response = await axios.post<SecurityAnalysis>(
    `${AGENT_HOST}/analyze/incoming`,
    {
      text,
      sender_id: senderId,
      use_ai: useAi
    },
    { timeout: 10000 }
  );

  return response.data;
};

/**
 * Agent 서버 상태 확인
 */
export const checkAgentHealth = async (): Promise<boolean> => {
  try {
    const response = await axios.get(`${AGENT_HOST}/health`, { timeout: 3000 });
    return response.data.status === 'ok';
  } catch {
    return false;
  }
};
