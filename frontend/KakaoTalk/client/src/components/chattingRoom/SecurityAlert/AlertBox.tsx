import React from 'react';
import styled from 'styled-components';
import { RiskLevel, RISK_COLORS } from '~/types/security';

const Box = styled.div<{ riskLevel: RiskLevel }>`
  background: white;
  border-radius: 16px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  border-top: 4px solid ${props => RISK_COLORS[props.riskLevel]};
`;

interface Props {
  riskLevel: RiskLevel;
  children: React.ReactNode;
  onClick?: (e: React.MouseEvent) => void;
}

const AlertBox: React.FC<Props> = ({ riskLevel, children, onClick }) => {
  return (
    <Box riskLevel={riskLevel} onClick={onClick}>
      {children}
    </Box>
  );
};

export default AlertBox;
