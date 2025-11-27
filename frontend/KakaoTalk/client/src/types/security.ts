/**
 * DualGuard 보안 분석 관련 타입 정의
 */

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface SecurityAnalysis {
  risk_level: RiskLevel;
  reasons: string[];
  recommended_action: string;
  is_secret_recommended: boolean;
}

export interface ImageAnalysisState {
  selectedImage: File | null;
  imagePreview: string | null;
  analysis: SecurityAnalysis | null;
  isAnalyzing: boolean;
}

// 위험도별 색상
export const RISK_COLORS: Record<RiskLevel, string> = {
  LOW: '#4CAF50',
  MEDIUM: '#FF9800',
  HIGH: '#f44336',
  CRITICAL: '#9C27B0'
};

// 위험도별 라벨
export const RISK_LABELS: Record<RiskLevel, string> = {
  LOW: '안전',
  MEDIUM: '주의 필요',
  HIGH: '위험 감지',
  CRITICAL: '심각한 위험'
};
