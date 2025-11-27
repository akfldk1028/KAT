import React from 'react';
import styled from 'styled-components';

const StyledButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: rgba(0, 0, 0, 0.05);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  & svg {
    width: 24px;
    height: 24px;
    fill: #666;
  }
`;

interface Props {
  icon: React.ReactNode;
  title?: string;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}

const IconButton: React.FC<Props> = ({ icon, title, onClick, disabled, className }) => {
  return (
    <StyledButton
      type="button"
      title={title}
      onClick={onClick}
      disabled={disabled}
      className={className}
    >
      {icon}
    </StyledButton>
  );
};

export default IconButton;
