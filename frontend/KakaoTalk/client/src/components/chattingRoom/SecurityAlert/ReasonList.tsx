import React from 'react';
import styled from 'styled-components';

const List = styled.ul`
  margin: 0 0 16px 0;
  padding: 0 0 0 20px;

  & li {
    margin-bottom: 8px;
    color: #666;
    font-size: 14px;
    line-height: 1.5;
  }
`;

interface Props {
  reasons: string[];
}

const ReasonList: React.FC<Props> = ({ reasons }) => {
  if (reasons.length === 0) {
    return null;
  }

  return (
    <List>
      {reasons.map((reason, index) => (
        <li key={index}>{reason}</li>
      ))}
    </List>
  );
};

export default ReasonList;
