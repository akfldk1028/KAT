import React from 'react';
import styled from 'styled-components';
import { SendIcon } from './Icons';

const Button = styled.button<{ isActive: boolean }>`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: ${props => props.isActive ? '#fee500' : '#e0e0e0'};
  cursor: ${props => props.isActive ? 'pointer' : 'default'};
  transition: all 0.2s;

  &:hover {
    background: ${props => props.isActive ? '#fada0a' : '#e0e0e0'};
  }

  & svg {
    width: 20px;
    height: 20px;
    fill: ${props => props.isActive ? '#3c1e1e' : '#999'};
  }
`;

interface Props {
  isActive: boolean;
  onClick: () => void;
}

const SendButton: React.FC<Props> = ({ isActive, onClick }) => {
  return (
    <Button
      type="button"
      isActive={isActive}
      onClick={onClick}
      title="전송"
    >
      <SendIcon />
    </Button>
  );
};

export default SendButton;
