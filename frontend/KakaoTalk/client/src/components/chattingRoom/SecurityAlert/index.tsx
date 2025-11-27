import React from 'react';
import styled from 'styled-components';
import { RiskLevel, SecurityAnalysis } from '~/types/security';
import AlertBox from './AlertBox';
import RiskBadge from './RiskBadge';
import ImagePreview from './ImagePreview';
import ReasonList from './ReasonList';
import RecommendedAction from './RecommendedAction';
import SecretRecommend from './SecretRecommend';
import ActionButtons from './ActionButtons';
import LoadingOverlay from './LoadingOverlay';

const Overlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  margin-bottom: 16px;
`;

const Title = styled.h3`
  margin: 0 0 0 12px;
  font-size: 18px;
  color: #333;
`;

interface Props {
  analysis: SecurityAnalysis;
  imagePreview?: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const getRiskTitle = (level: RiskLevel): string => {
  switch (level) {
    case 'LOW': return '안전';
    case 'MEDIUM': return '주의 필요';
    case 'HIGH': return '위험 감지';
    case 'CRITICAL': return '심각한 위험';
    default: return '분석 완료';
  }
};

const SecurityAlert: React.FC<Props> = ({
  analysis,
  imagePreview,
  onConfirm,
  onCancel,
  isLoading = false
}) => {
  if (isLoading) {
    return <LoadingOverlay />;
  }

  const handleBoxClick = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

  return (
    <Overlay onClick={onCancel}>
      <AlertBox riskLevel={analysis.risk_level} onClick={handleBoxClick}>
        <Header>
          <RiskBadge level={analysis.risk_level} />
          <Title>{getRiskTitle(analysis.risk_level)}</Title>
        </Header>

        {imagePreview && <ImagePreview src={imagePreview} />}

        <ReasonList reasons={analysis.reasons} />

        <RecommendedAction action={analysis.recommended_action} />

        {analysis.is_secret_recommended && <SecretRecommend />}

        <ActionButtons
          riskLevel={analysis.risk_level}
          onConfirm={onConfirm}
          onCancel={onCancel}
        />
      </AlertBox>
    </Overlay>
  );
};

export default SecurityAlert;
