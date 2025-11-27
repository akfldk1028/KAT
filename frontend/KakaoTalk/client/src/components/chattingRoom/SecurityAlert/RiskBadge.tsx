import React from 'react';
import styled from 'styled-components';
import { RiskLevel, RISK_COLORS } from '~/types/security';

const Badge = styled.span<{ color: string }>`
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: bold;
  color: white;
  background: ${props => props.color};
`;

interface Props {
  level: RiskLevel;
}

const RiskBadge: React.FC<Props> = ({ level }) => {
  return (
    <Badge color={RISK_COLORS[level]}>
      {level}
    </Badge>
  );
};

export default RiskBadge;
