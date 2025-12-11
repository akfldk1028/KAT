import React, { useState, useEffect } from 'react';
import styled, { keyframes } from 'styled-components';
import { viewSecretMessage, SecretMessageContent } from '~/apis/secret';
import { HOST } from '~/constants';

const fadeIn = keyframes`
  from { opacity: 0; }
  to { opacity: 1; }
`;

const slideUp = keyframes`
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

const Overlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
  animation: ${fadeIn} 0.2s ease;
`;

const ViewerBox = styled.div`
  background: #ffffff;
  border-radius: 20px;
  width: 320px;
  max-width: 90%;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  position: relative;
  overflow: hidden;
  animation: ${slideUp} 0.3s ease;
`;

const Header = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 20px 16px;
  border-bottom: 1px solid #f0f0f0;
`;

const LockIcon = styled.div`
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #FFE812 0%, #FFC700 100%);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  margin-bottom: 12px;
  box-shadow: 0 4px 12px rgba(255, 199, 0, 0.3);
`;

const Title = styled.h3`
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: #1a1a1a;
`;

const TimerSection = styled.div`
  padding: 16px 20px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
`;

const TimerDisplay = styled.div<{ isUrgent: boolean }>`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  & .timer-icon {
    font-size: 18px;
  }

  & .timer-text {
    font-size: 24px;
    font-weight: 700;
    font-family: 'SF Mono', 'Menlo', monospace;
    color: ${({ isUrgent }) => isUrgent ? '#FF3B30' : '#1a1a1a'};
    letter-spacing: -0.5px;
  }

  & .timer-label {
    font-size: 13px;
    color: #888;
    margin-top: 4px;
  }
`;

const ProgressBar = styled.div`
  height: 3px;
  background: #e5e5e5;
  border-radius: 2px;
  margin-top: 12px;
  overflow: hidden;
`;

const ProgressFill = styled.div<{ progress: number; isUrgent: boolean }>`
  height: 100%;
  width: ${({ progress }) => progress}%;
  background: ${({ isUrgent }) => isUrgent
    ? 'linear-gradient(90deg, #FF3B30, #FF6B6B)'
    : 'linear-gradient(90deg, #FFE812, #FFC700)'};
  transition: width 1s linear;
  border-radius: 2px;
`;

const ContentSection = styled.div`
  padding: 20px;
  max-height: 400px;
  overflow-y: auto;
`;

const MessageBox = styled.div<{ preventCapture?: boolean }>`
  background: #f5f5f5;
  border-radius: 16px;
  padding: 16px;
  font-size: 15px;
  line-height: 1.6;
  color: #1a1a1a;
  word-break: break-word;
  white-space: pre-wrap;

  /* 캡처 방지 CSS */
  ${({ preventCapture }) => preventCapture && `
    user-select: none;
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    -webkit-touch-callout: none;
    -webkit-user-drag: none;
    pointer-events: auto;
  `}
`;

const SecretImage = styled.img`
  max-width: 100%;
  max-height: 280px;
  border-radius: 12px;
  display: block;
  margin: 0 auto;
`;

const WarningBadge = styled.div`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%);
  color: white;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  margin-top: 8px;
`;

const FooterSection = styled.div`
  padding: 16px 20px 20px;
`;

const CloseButton = styled.button`
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #FFE812 0%, #FFC700 100%);
  color: #1a1a1a;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(255, 199, 0, 0.4);
  }

  &:active {
    transform: translateY(0);
  }
`;

const LoadingSpinner = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px 20px;
  color: #888;
  gap: 12px;

  & .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid #f0f0f0;
    border-top-color: #FFC700;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;

const ExpiredMessage = styled.div`
  text-align: center;
  padding: 40px 20px;

  & .icon {
    width: 64px;
    height: 64px;
    background: #f5f5f5;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    margin: 0 auto 16px;
  }

  & .title {
    font-size: 16px;
    font-weight: 600;
    color: #1a1a1a;
    margin-bottom: 4px;
  }

  & .text {
    font-size: 13px;
    color: #888;
  }
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
    if (!content || content.is_expired) return;
    if (remainingSeconds <= 0) return;

    const timer = setTimeout(() => {
      setRemainingSeconds(prev => prev - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [content, remainingSeconds]);

  // MM:SS 포맷
  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const progress = totalSeconds > 0 ? (remainingSeconds / totalSeconds) * 100 : 0;
  const isUrgent = remainingSeconds <= 30; // 30초 이하면 긴급

  return (
    <Overlay onClick={onClose}>
      <ViewerBox onClick={(e) => e.stopPropagation()}>
        <Header>
          <LockIcon>🔒</LockIcon>
          <Title>시크릿 메시지</Title>
          {content && content.prevent_capture && (
            <WarningBadge>
              <span>📵</span>
              캡처 방지 활성화
            </WarningBadge>
          )}
        </Header>

        {loading && (
          <LoadingSpinner>
            <div className="spinner" />
            <span>불러오는 중...</span>
          </LoadingSpinner>
        )}

        {error === 'expired' && (
          <ExpiredMessage>
            <div className="icon">⏰</div>
            <div className="title">메시지 만료</div>
            <div className="text">이 메시지는 더 이상 볼 수 없습니다</div>
          </ExpiredMessage>
        )}

        {error === 'failed' && (
          <ExpiredMessage>
            <div className="icon">❌</div>
            <div className="title">불러오기 실패</div>
            <div className="text">메시지를 불러올 수 없습니다</div>
          </ExpiredMessage>
        )}

        {content && !error && (
          <>
            <TimerSection>
              <TimerDisplay isUrgent={isUrgent}>
                <span className="timer-icon">{isUrgent ? '🔥' : '⏱️'}</span>
                <span className="timer-text">{formatTime(remainingSeconds)}</span>
              </TimerDisplay>
              <ProgressBar>
                <ProgressFill progress={progress} isUrgent={isUrgent} />
              </ProgressBar>
            </TimerSection>

            <ContentSection>
              <MessageBox preventCapture={content.prevent_capture}>
                {content.message_type === 'image' ? (
                  <SecretImage
                    src={content.message.startsWith('http') ? content.message : `${HOST}${content.message}`}
                    alt="시크릿 이미지"
                    draggable={false}
                    onContextMenu={(e) => content.prevent_capture && e.preventDefault()}
                  />
                ) : (
                  content.message
                )}
              </MessageBox>
            </ContentSection>
          </>
        )}

        <FooterSection>
          <CloseButton onClick={onClose}>
            닫기
          </CloseButton>
        </FooterSection>
      </ViewerBox>
    </Overlay>
  );
};

export default SecretMessageViewer;
