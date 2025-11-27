import React, { useState } from 'react';
import styled from 'styled-components';

const Overlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1001;
`;

const PopupBox = styled.div`
  background: white;
  border-radius: 16px;
  padding: 24px;
  width: 340px;
  max-width: 90%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
`;

const Title = styled.h3`
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
  text-align: center;
`;

const Subtitle = styled.p`
  margin: 0 0 20px 0;
  font-size: 13px;
  color: #888;
  text-align: center;
`;

const OptionGroup = styled.div`
  margin-bottom: 20px;
`;

const OptionLabel = styled.label`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: #f9fafb;
  border-radius: 12px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #f3f4f6;
  }
`;

const OptionInfo = styled.div`
  display: flex;
  flex-direction: column;
`;

const OptionTitle = styled.span`
  font-size: 14px;
  font-weight: 500;
  color: #333;
`;

const OptionDesc = styled.span`
  font-size: 12px;
  color: #888;
  margin-top: 2px;
`;

const Toggle = styled.div<{ active: boolean }>`
  width: 44px;
  height: 24px;
  background: ${({ active }) => (active ? '#3b82f6' : '#d1d5db')};
  border-radius: 12px;
  position: relative;
  transition: all 0.2s;

  &::after {
    content: '';
    position: absolute;
    top: 2px;
    left: ${({ active }) => (active ? '22px' : '2px')};
    width: 20px;
    height: 20px;
    background: white;
    border-radius: 50%;
    transition: all 0.2s;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }
`;

const SelectGroup = styled.div`
  margin-top: 8px;
  padding-left: 16px;
`;

const SelectLabel = styled.span`
  font-size: 12px;
  color: #666;
  margin-right: 8px;
`;

const Select = styled.select`
  padding: 6px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 13px;
  color: #333;
  background: white;
  cursor: pointer;

  &:focus {
    outline: none;
    border-color: #3b82f6;
  }
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 12px;
  margin-top: 24px;
`;

const Button = styled.button<{ variant?: 'primary' | 'secondary' }>`
  flex: 1;
  padding: 12px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  ${({ variant }) =>
    variant === 'primary'
      ? `
        background: #3b82f6;
        color: white;
        &:hover { background: #2563eb; }
      `
      : `
        background: #f3f4f6;
        color: #374151;
        &:hover { background: #e5e7eb; }
      `}
`;

export interface SecretOptions {
  expirySeconds: number;     // 열람기한 (초 단위)
  requireAuth: boolean;      // 본인인증 필요
  preventCapture: boolean;   // 캡처방지
}

interface Props {
  onConfirm: (options: SecretOptions) => void;
  onCancel: () => void;
}

const SecretModePopup: React.FC<Props> = ({ onConfirm, onCancel }) => {
  const [expirySeconds, setExpirySeconds] = useState(60);  // 기본 1분
  const [requireAuth, setRequireAuth] = useState(false);
  const [preventCapture, setPreventCapture] = useState(true);

  const handleConfirm = () => {
    onConfirm({
      expirySeconds,
      requireAuth,
      preventCapture
    });
  };

  return (
    <Overlay onClick={onCancel}>
      <PopupBox onClick={(e) => e.stopPropagation()}>
        <Title>시크릿 전송 설정</Title>
        <Subtitle>민감정보를 안전하게 보호합니다</Subtitle>

        <OptionGroup>
          {/* 열람기한 */}
          <OptionLabel>
            <OptionInfo>
              <OptionTitle>열람 기한</OptionTitle>
              <OptionDesc>설정 시간 후 메시지가 자동 삭제됩니다</OptionDesc>
            </OptionInfo>
          </OptionLabel>
          <SelectGroup>
            <SelectLabel>삭제 시간:</SelectLabel>
            <Select
              value={expirySeconds}
              onChange={(e) => setExpirySeconds(Number(e.target.value))}
            >
              <option value={10}>10초 (테스트)</option>
              <option value={30}>30초 (테스트)</option>
              <option value={60}>1분</option>
              <option value={300}>5분</option>
              <option value={3600}>1시간</option>
              <option value={86400}>24시간</option>
            </Select>
          </SelectGroup>

          {/* 본인인증 */}
          <OptionLabel onClick={() => setRequireAuth(!requireAuth)}>
            <OptionInfo>
              <OptionTitle>본인 인증</OptionTitle>
              <OptionDesc>상대방이 열람 시 본인 인증이 필요합니다</OptionDesc>
            </OptionInfo>
            <Toggle active={requireAuth} />
          </OptionLabel>

          {/* 캡처방지 */}
          <OptionLabel onClick={() => setPreventCapture(!preventCapture)}>
            <OptionInfo>
              <OptionTitle>캡처 방지</OptionTitle>
              <OptionDesc>스크린샷 및 화면 녹화를 차단합니다</OptionDesc>
            </OptionInfo>
            <Toggle active={preventCapture} />
          </OptionLabel>
        </OptionGroup>

        <ButtonGroup>
          <Button variant="secondary" onClick={onCancel}>
            취소
          </Button>
          <Button variant="primary" onClick={handleConfirm}>
            시크릿 전송
          </Button>
        </ButtonGroup>
      </PopupBox>
    </Overlay>
  );
};

export default SecretModePopup;
