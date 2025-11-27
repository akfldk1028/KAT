import React from 'react';
import styled from 'styled-components';
import { SecurityAnalysis } from '~/types/security';

const Overlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
`;

const AlertBox = styled.div`
  background: white;
  border-radius: 16px;
  padding: 24px;
  width: 320px;
  max-width: 90%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
`;

const Title = styled.h3`
  margin: 0 0 16px 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
  text-align: center;
`;

const RiskBadge = styled.span<{ level: string }>`
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 16px;
  ${({ level }) => {
    switch (level) {
      case 'CRITICAL':
        return 'background: #fee2e2; color: #dc2626;';
      case 'HIGH':
        return 'background: #ffedd5; color: #ea580c;';
      case 'MEDIUM':
        return 'background: #fef3c7; color: #d97706;';
      default:
        return 'background: #d1fae5; color: #059669;';
    }
  }}
`;

const RiskLabel = styled.div`
  text-align: center;
  margin-bottom: 16px;
`;

const ReasonList = styled.ul`
  margin: 0 0 16px 0;
  padding: 0 0 0 20px;
  font-size: 14px;
  color: #666;
`;

const ReasonItem = styled.li`
  margin-bottom: 8px;
  line-height: 1.4;
`;

const ImagePreview = styled.img`
  width: 100%;
  max-height: 150px;
  object-fit: contain;
  border-radius: 8px;
  margin-bottom: 16px;
  background: #f5f5f5;
`;

const LoadingBox = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
`;

const Spinner = styled.div`
  width: 40px;
  height: 40px;
  border: 3px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
`;

const LoadingText = styled.p`
  color: #666;
  font-size: 14px;
  margin: 0;
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 12px;
`;

const Button = styled.button<{ variant?: 'primary' | 'secondary' | 'danger' }>`
  flex: 1;
  padding: 12px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  ${({ variant }) => {
    switch (variant) {
      case 'primary':
        return `
          background: #3b82f6;
          color: white;
          &:hover { background: #2563eb; }
        `;
      case 'danger':
        return `
          background: #ef4444;
          color: white;
          &:hover { background: #dc2626; }
        `;
      default:
        return `
          background: #f3f4f6;
          color: #374151;
          &:hover { background: #e5e7eb; }
        `;
    }
  }}
`;

interface Props {
  analysis: SecurityAnalysis;
  imagePreview?: string;
  isLoading?: boolean;
  onSecretSend: () => void;  // 시크릿 전송 클릭
  onNormalSend: () => void;  // 그냥 보내기 클릭
  onCancel: () => void;      // 취소 (로딩 중)
}

const SecurityAlert: React.FC<Props> = ({
  analysis,
  imagePreview,
  isLoading,
  onSecretSend,
  onNormalSend,
  onCancel
}) => {
  if (isLoading) {
    return (
      <Overlay>
        <AlertBox>
          <LoadingBox>
            <Spinner />
            <LoadingText>AI가 메시지를 분석하고 있습니다...</LoadingText>
          </LoadingBox>
        </AlertBox>
      </Overlay>
    );
  }

  const getRiskText = (level: string) => {
    switch (level) {
      case 'CRITICAL': return '매우 위험';
      case 'HIGH': return '높은 위험';
      case 'MEDIUM': return '주의 필요';
      default: return '안전';
    }
  };

  return (
    <Overlay onClick={onCancel}>
      <AlertBox onClick={(e) => e.stopPropagation()}>
        <Title>민감정보가 감지되었습니다</Title>

        <RiskLabel>
          <RiskBadge level={analysis.risk_level}>
            {getRiskText(analysis.risk_level)}
          </RiskBadge>
        </RiskLabel>

        {imagePreview && <ImagePreview src={imagePreview} alt="분석 이미지" />}

        {analysis.reasons.length > 0 && (
          <ReasonList>
            {analysis.reasons.map((reason, index) => (
              <ReasonItem key={index}>{reason}</ReasonItem>
            ))}
          </ReasonList>
        )}

        <ButtonGroup>
          <Button variant="secondary" onClick={onNormalSend}>
            그냥 보내기
          </Button>
          <Button variant="primary" onClick={onSecretSend}>
            시크릿 전송
          </Button>
        </ButtonGroup>
      </AlertBox>
    </Overlay>
  );
};

export default SecurityAlert;

