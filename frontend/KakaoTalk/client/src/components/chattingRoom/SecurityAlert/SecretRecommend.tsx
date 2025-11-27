import React from 'react';
import styled from 'styled-components';

const Wrapper = styled.div`
  background: #fff3e0;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;

  & svg {
    width: 24px;
    height: 24px;
    margin-right: 12px;
    fill: #FF9800;
  }

  & span {
    font-size: 14px;
    color: #e65100;
    font-weight: 500;
  }
`;

const ShieldIcon: React.FC = () => (
  <svg viewBox="0 0 24 24">
    <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/>
  </svg>
);

const SecretRecommend: React.FC = () => {
  return (
    <Wrapper>
      <ShieldIcon />
      <span>시크릿 전송을 권장합니다</span>
    </Wrapper>
  );
};

export default SecretRecommend;
