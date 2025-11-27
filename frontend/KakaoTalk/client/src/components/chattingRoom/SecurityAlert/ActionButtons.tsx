import React from 'react';
import styled from 'styled-components';
import { RiskLevel } from '~/types/security';

const ButtonGroup = styled.div`
  display: flex;
  gap: 12px;
`;

const Button = styled.button<{ variant: 'primary' | 'secondary' | 'danger' }>`
  flex: 1;
  padding: 12px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  ${props => {
    switch (props.variant) {
      case 'primary':
        return `
          background: #ffeb33;
          color: #000;
          &:hover { background: #ffe000; }
        `;
      case 'secondary':
        return `
          background: #eee;
          color: #333;
          &:hover { background: #ddd; }
        `;
      case 'danger':
        return `
          background: #f44336;
          color: white;
          &:hover { background: #d32f2f; }
        `;
    }
  }}

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

interface Props {
  riskLevel: RiskLevel;
  onConfirm: () => void;
  onCancel: () => void;
}

const ActionButtons: React.FC<Props> = ({ riskLevel, onConfirm, onCancel }) => {
  const isSafe = riskLevel === 'LOW';
  const isDangerous = riskLevel === 'HIGH' || riskLevel === 'CRITICAL';

  return (
    <ButtonGroup>
      <Button variant="secondary" onClick={onCancel}>
        취소
      </Button>
      {isSafe ? (
        <Button variant="primary" onClick={onConfirm}>
          전송
        </Button>
      ) : isDangerous ? (
        <Button variant="danger" onClick={onConfirm}>
          위험 감수하고 전송
        </Button>
      ) : (
        <Button variant="primary" onClick={onConfirm}>
          확인 후 전송
        </Button>
      )}
    </ButtonGroup>
  );
};

export default ActionButtons;
