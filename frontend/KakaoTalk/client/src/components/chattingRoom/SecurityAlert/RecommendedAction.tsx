import React from 'react';
import styled from 'styled-components';

const Wrapper = styled.div`
  background: #f5f5f5;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 20px;

  & strong {
    display: block;
    font-size: 12px;
    color: #999;
    margin-bottom: 4px;
  }

  & p {
    margin: 0;
    font-size: 14px;
    color: #333;
  }
`;

interface Props {
  action: string;
}

const RecommendedAction: React.FC<Props> = ({ action }) => {
  return (
    <Wrapper>
      <strong>권장 조치</strong>
      <p>{action}</p>
    </Wrapper>
  );
};

export default RecommendedAction;
