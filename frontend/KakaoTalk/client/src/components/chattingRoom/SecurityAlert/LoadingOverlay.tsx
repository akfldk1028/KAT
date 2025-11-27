import React from 'react';
import styled, { keyframes } from 'styled-components';

const spin = keyframes`
  to { transform: rotate(360deg); }
`;

const Overlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  color: white;
`;

const Spinner = styled.div`
  width: 48px;
  height: 48px;
  border: 4px solid #fff;
  border-top-color: #ffeb33;
  border-radius: 50%;
  animation: ${spin} 1s linear infinite;
  margin-bottom: 16px;
`;

const Title = styled.p`
  font-size: 16px;
  margin: 0 0 8px 0;
`;

const Subtitle = styled.p`
  font-size: 14px;
  opacity: 0.7;
  margin: 0;
`;

interface Props {
  title?: string;
  subtitle?: string;
}

const LoadingOverlay: React.FC<Props> = ({
  title = '이미지를 분석하고 있습니다...',
  subtitle = 'Vision AI가 민감정보를 검사 중입니다'
}) => {
  return (
    <Overlay>
      <Spinner />
      <Title>{title}</Title>
      <Subtitle>{subtitle}</Subtitle>
    </Overlay>
  );
};

export default LoadingOverlay;
