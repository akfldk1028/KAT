import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { viewSecretMessage, SecretMessageContent } from '~/apis/secret';

const Overlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
`;

const ViewerBox = styled.div`
  background: white;
  border-radius: 16px;
  padding: 24px;
  width: 360px;
  max-width: 90%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  position: relative;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  gap: 8px;
`;

const LockIcon = styled.span`
  font-size: 24px;
`;

const Title = styled.h3`
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
`;

const MessageBox = styled.div`
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
  min-height: 100px;
  margin-bottom: 16px;
  font-size: 15px;
  line-height: 1.6;
  color: #333;
  word-break: break-word;
  white-space: pre-wrap;
`;

const InfoText = styled.p`
  font-size: 12px;
  color: #888;
  text-align: center;
  margin: 0 0 16px 0;
`;

const TimerBar = styled.div<{ progress: number }>`
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  margin-bottom: 16px;
  overflow: hidden;

  &::after {
    content: '';
    display: block;
    height: 100%;
    width: ${({ progress }) => progress}%;
    background: linear-gradient(90deg, #ef4444, #f97316);
    transition: width 1s linear;
  }
`;

const CloseButton = styled.button`
  width: 100%;
  padding: 12px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #2563eb;
  }
`;

const LoadingSpinner = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100px;
  color: #888;
`;

const ExpiredMessage = styled.div`
  text-align: center;
  padding: 40px 20px;
  color: #888;
  
  & .icon {
    font-size: 48px;
    margin-bottom: 12px;
  }
  
  & .text {
    font-size: 14px;
  }
`;

const WarningBadge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #fef3c7;
  color: #92400e;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  margin-bottom: 12px;
`;

interface Props {
  secretId: string;
  onClose: () => void;
}

const SecretMessageViewer: React.FC<Props> = ({ secretId, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [content, setContent] = useState<SecretMessageContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [totalSeconds, setTotalSeconds] = useState(0);

  useEffect(() => {
    const fetchContent = async () => {
      try {
        const data = await viewSecretMessage(secretId);
        setContent(data);
        setRemainingSeconds(data.remaining_seconds);
        setTotalSeconds(data.remaining_seconds);
      } catch (err) {
        const axiosErr = err as { response?: { status: number } };
        if (axiosErr.response?.status === 410) {
          setError('expired');
        } else {
          setError('failed');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchContent();
  }, [secretId]);

  // 타이머 카운트다운
  useEffect(() => {
    if (!content || content.is_expired || remainingSeconds <= 0) return;

    const timer = setInterval(() => {
      setRemainingSeconds(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [content]);

  const formatTime = (seconds: number) => {
    if (seconds >= 3600) {
      const h = Math.floor(seconds / 3600);
      const m = Math.floor((seconds % 3600) / 60);
      return `${h}시간 ${m}분`;
    } else if (seconds >= 60) {
      const m = Math.floor(seconds / 60);
      const s = seconds % 60;
      return `${m}분 ${s}초`;
    }
    return `${seconds}초`;
  };

  const progress = totalSeconds > 0 ? (remainingSeconds / totalSeconds) * 100 : 0;

  return (
    <Overlay onClick={onClose}>
      <ViewerBox onClick={(e) => e.stopPropagation()}>
        <Header>
          <LockIcon>🔒</LockIcon>
          <Title>시크릿 메시지</Title>
        </Header>

        {loading && (
          <LoadingSpinner>불러오는 중...</LoadingSpinner>
        )}

        {error === 'expired' && (
          <ExpiredMessage>
            <div className="icon">⏰</div>
            <div className="text">메시지가 만료되었습니다</div>
          </ExpiredMessage>
        )}

        {error === 'failed' && (
          <ExpiredMessage>
            <div className="icon">❌</div>
            <div className="text">메시지를 불러올 수 없습니다</div>
          </ExpiredMessage>
        )}

        {content && !error && (
          <>
            {content.prevent_capture && (
              <WarningBadge>
                <span>📵</span>
                캡처 방지 활성화
              </WarningBadge>
            )}
            
            {remainingSeconds > 0 ? (
              <>
                <TimerBar progress={progress} />
                <InfoText>
                  남은 시간: {formatTime(remainingSeconds)}
                </InfoText>
              </>
            ) : (
              <InfoText style={{ color: '#ef4444' }}>
                메시지가 곧 삭제됩니다
              </InfoText>
            )}

            <MessageBox>
              {content.message}
            </MessageBox>
          </>
        )}

        <CloseButton onClick={onClose}>
          닫기
        </CloseButton>
      </ViewerBox>
    </Overlay>
  );
};

export default SecretMessageViewer;
