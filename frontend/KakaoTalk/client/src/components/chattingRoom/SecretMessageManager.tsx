/**
 * SecretMessageManager - 발신자용 시크릿 메시지 관리 컴포넌트
 * 기능: 열람 상태 확인, 수동 삭제
 */
import React, { useState, useEffect } from 'react';
import styled, { keyframes } from 'styled-components';
import { checkSecretStatus, expireSecretMessage, extendSecretMessage, SecretMessageStatus } from '~/apis/secret';
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

const ManagerBox = styled.div`
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
  background: linear-gradient(135deg, #ffeb33 0%, #ffc700 100%);
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

const StatusSection = styled.div`
  padding: 20px;
`;

const StatusItem = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 12px;
  margin-bottom: 10px;

  &:last-child {
    margin-bottom: 0;
  }
`;

const StatusLabel = styled.span`
  font-size: 14px;
  color: #666;
`;

const StatusValue = styled.span<{ color?: string }>`
  font-size: 14px;
  font-weight: 600;
  color: ${({ color }) => color || '#1a1a1a'};
`;

const StatusBadge = styled.span<{ viewed?: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  background: ${({ viewed }) => viewed ? '#dcfce7' : '#fef3c7'};
  color: ${({ viewed }) => viewed ? '#166534' : '#92400e'};
`;

const MessagePreviewSection = styled.div`
  padding: 16px 20px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
`;

const PreviewLabel = styled.div`
  font-size: 12px;
  color: #888;
  margin-bottom: 8px;
`;

const PreviewBox = styled.div`
  background: white;
  border-radius: 12px;
  padding: 12px;
  border: 1px solid #e5e7eb;
`;

const PreviewText = styled.div`
  font-size: 14px;
  color: #333;
  line-height: 1.5;
  word-break: break-word;
  white-space: pre-wrap;
  max-height: 100px;
  overflow-y: auto;
`;

const PreviewImage = styled.img`
  max-width: 100%;
  max-height: 150px;
  border-radius: 8px;
  display: block;
`;

const FooterSection = styled.div`
  padding: 16px 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
`;

const ExtendSection = styled.div`
  margin-bottom: 10px;
`;

const ExtendLabel = styled.div`
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
  text-align: center;
`;

const ExtendOptions = styled.div`
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
`;

const ExtendButton = styled.button<{ selected?: boolean }>`
  padding: 8px 14px;
  border: 2px solid ${({ selected }) => selected ? '#ffeb33' : '#e5e7eb'};
  border-radius: 20px;
  background: ${({ selected }) => selected ? '#fffde7' : 'white'};
  color: ${({ selected }) => selected ? '#b8860b' : '#666'};
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: #ffeb33;
    background: #fffde7;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const ApplyExtendButton = styled.button`
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #ffeb33 0%, #ffc700 100%);
  color: #000;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 8px;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(255, 199, 0, 0.4);
  }

  &:active {
    transform: translateY(0);
  }

  &:disabled {
    background: #d1d5db;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
`;

const DeleteButton = styled.button`
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #888 0%, #666 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(100, 100, 100, 0.4);
  }

  &:active {
    transform: translateY(0);
  }

  &:disabled {
    background: #d1d5db;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
`;

const CloseButton = styled.button`
  width: 100%;
  padding: 14px;
  background: #eee;
  color: #333;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #ddd;
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
    border-top-color: #ffeb33;
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
  onDeleted?: () => void;
}

// 시간 연장 옵션 (초 단위)
const EXTEND_OPTIONS = [
  { label: '+1분', seconds: 60 },
  { label: '+5분', seconds: 300 },
  { label: '+10분', seconds: 600 },
  { label: '+30분', seconds: 1800 },
];

const SecretMessageManager: React.FC<Props> = ({ secretId, onClose, onDeleted }) => {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<SecretMessageStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [extending, setExtending] = useState(false);
  const [selectedExtendTime, setSelectedExtendTime] = useState<number | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await checkSecretStatus(secretId);
        setStatus(data);
      } catch (err) {
        setError('상태를 불러올 수 없습니다');
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
  }, [secretId]);

  const handleDelete = async () => {
    if (!confirm('이 시크릿 메시지를 삭제하시겠습니까?\n상대방도 더 이상 볼 수 없습니다.')) {
      return;
    }

    setDeleting(true);
    try {
      await expireSecretMessage(secretId);
      setDeleted(true);
      onDeleted?.();
    } catch (err) {
      alert('삭제에 실패했습니다');
    } finally {
      setDeleting(false);
    }
  };

  const handleExtend = async () => {
    if (!selectedExtendTime) {
      alert('연장할 시간을 선택해주세요');
      return;
    }

    setExtending(true);
    try {
      const result = await extendSecretMessage(secretId, selectedExtendTime);
      // 상태 업데이트
      setStatus(prev => prev ? {
        ...prev,
        remaining_seconds: result.remaining_seconds,
        expires_at: result.new_expires_at
      } : prev);
      setSelectedExtendTime(null);
      alert(`시간이 ${selectedExtendTime / 60}분 연장되었습니다`);
    } catch (err) {
      alert('시간 연장에 실패했습니다');
    } finally {
      setExtending(false);
    }
  };

  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatRemaining = (seconds: number) => {
    if (seconds <= 0) return '만료됨';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    if (m > 60) {
      const h = Math.floor(m / 60);
      return `${h}시간 ${m % 60}분`;
    }
    return `${m}분 ${s}초`;
  };

  return (
    <Overlay onClick={onClose}>
      <ManagerBox onClick={(e) => e.stopPropagation()}>
        <Header>
          <LockIcon>⚙️</LockIcon>
          <Title>시크릿 메시지 관리</Title>
        </Header>

        {loading && (
          <LoadingSpinner>
            <div className="spinner" />
            <span>불러오는 중...</span>
          </LoadingSpinner>
        )}

        {error && (
          <ExpiredMessage>
            <div className="icon">❌</div>
            <div className="title">오류</div>
            <div className="text">{error}</div>
          </ExpiredMessage>
        )}

        {deleted && (
          <ExpiredMessage>
            <div className="icon">🗑️</div>
            <div className="title">삭제 완료</div>
            <div className="text">메시지가 삭제되었습니다</div>
          </ExpiredMessage>
        )}

        {/* 메시지 미리보기 */}
        {status && !deleted && !error && status.message && (
          <MessagePreviewSection>
            <PreviewLabel>📝 보낸 내용</PreviewLabel>
            <PreviewBox>
              {status.message_type === 'image' ? (
                <PreviewImage
                  src={status.message.startsWith('http') ? status.message : `${HOST}${status.message}`}
                  alt="보낸 이미지"
                />
              ) : (
                <PreviewText>{status.message}</PreviewText>
              )}
            </PreviewBox>
          </MessagePreviewSection>
        )}

        {status && !deleted && !error && (
          <StatusSection>
            <StatusItem>
              <StatusLabel>열람 상태</StatusLabel>
              <StatusBadge viewed={status.is_viewed}>
                {status.is_viewed ? '✓ 읽음' : '○ 안읽음'}
              </StatusBadge>
            </StatusItem>

            {status.is_viewed && status.viewed_at && (
              <StatusItem>
                <StatusLabel>열람 일시</StatusLabel>
                <StatusValue>{formatDateTime(status.viewed_at)}</StatusValue>
              </StatusItem>
            )}

            <StatusItem>
              <StatusLabel>만료 상태</StatusLabel>
              <StatusValue color={status.is_expired ? '#ef4444' : '#22c55e'}>
                {status.is_expired ? '만료됨' : '유효'}
              </StatusValue>
            </StatusItem>

            {!status.is_expired && (
              <StatusItem>
                <StatusLabel>남은 시간</StatusLabel>
                <StatusValue color={status.remaining_seconds < 60 ? '#ef4444' : '#1a1a1a'}>
                  {formatRemaining(status.remaining_seconds)}
                </StatusValue>
              </StatusItem>
            )}

            <StatusItem>
              <StatusLabel>생성 일시</StatusLabel>
              <StatusValue>{formatDateTime(status.created_at)}</StatusValue>
            </StatusItem>
          </StatusSection>
        )}

        <FooterSection>
          {status && !deleted && !status.is_expired && (
            <>
              <ExtendSection>
                <ExtendLabel>⏱️ 시간 연장</ExtendLabel>
                <ExtendOptions>
                  {EXTEND_OPTIONS.map(opt => (
                    <ExtendButton
                      key={opt.seconds}
                      selected={selectedExtendTime === opt.seconds}
                      onClick={() => setSelectedExtendTime(opt.seconds)}
                      disabled={extending}
                    >
                      {opt.label}
                    </ExtendButton>
                  ))}
                </ExtendOptions>
                {selectedExtendTime && (
                  <ApplyExtendButton onClick={handleExtend} disabled={extending}>
                    {extending ? '연장 중...' : '⏱️ 시간 연장하기'}
                  </ApplyExtendButton>
                )}
              </ExtendSection>

              <DeleteButton onClick={handleDelete} disabled={deleting || extending}>
                {deleting ? '삭제 중...' : '🗑️ 메시지 삭제'}
              </DeleteButton>
            </>
          )}
          <CloseButton onClick={onClose}>
            닫기
          </CloseButton>
        </FooterSection>
      </ManagerBox>
    </Overlay>
  );
};

export default SecretMessageManager;
