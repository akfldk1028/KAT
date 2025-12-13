import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { UserResponseDto } from '~/types/user';
import { SecurityAnalysis } from '~/types/security';
import { BASE_IMG_URL, HOST } from '~/constants';
import { SeparationBlock } from './InfoBlock';
import SecretMessageViewer from './SecretMessageViewer';
import SecretMessageManager from './SecretMessageManager';
import ImageViewerModal from './ImageViewerModal';
import { checkSecretStatus, SecretMessageStatus } from '~/apis/secret';

// 채팅방에서 채팅을 나타내는 컴포넌트
const ChatWrapper = styled.div`
  position: relative;
  display: inline-block;
  padding: 7px 8px;
  border-radius: 4px;
  margin-bottom: 7px;
  box-shadow: 0px 1px 2px 0px #8fabc7;
  max-width: 70%;
  word-wrap: break-word;
  white-space: pre-wrap;
`;
const RightBlock = styled.div`
  text-align: right;
  margin-top: 10px;
  margin-left: 10px;
  margin-right: 10px;

  & ${ChatWrapper} {
    background-color: #ffec42;
    text-align: left;
    & span {
      position: absolute;
      display: inline-block;
      &.time {
        min-width: 65px;
        text-align: right;
        bottom: 0;
        left: -70px;
      }
      &.not-read {
        color: #ffec42;
        min-width: 30px;
        text-align: right;
        bottom: 16px;
        left: -35px;
      }
    }
  }
`;
const LeftBlock = styled.div`
  position: relative;
  margin-top: 10px;
  margin-left: 10px;
  margin-right: 10px;
  padding-left: 50px;
  & ${ChatWrapper} {
    background-color: #fff;
    & span {
      position: absolute;
      &.time {
        min-width: 65px;
        text-align: left;
        bottom: 0;
        right: -70px;
      }
      &.not-read {
        color: #ffec42;
        min-width: 30px;
        text-align: left;
        bottom: 16px;
        right: -35px;
      }
    }
  }
  & > img {
    position: absolute;
    top: 3px;
    left: 0;
    height: 45px;
    width: 45px;
    border-radius: 20px;
    float: left;
    cursor: pointer;
  }
`;
const NameBlock = styled.div`
  margin-bottom: 5px;
`;

// 이미지 메시지 스타일
const ImageWrapper = styled.div`
  position: relative;
  display: inline-block;
  border-radius: 8px;
  margin-bottom: 7px;
  max-width: 200px;
  overflow: hidden;
  box-shadow: 0px 1px 2px 0px #8fabc7;
  cursor: pointer;

  & img {
    width: 100%;
    height: auto;
    display: block;
  }
`;

// 에이전트 알림 메시지 스타일
const AgentAlertWrapper = styled.div`
  width: 100%;
  display: flex;
  justify-content: center;
  margin: 16px 0;
`;

const AgentAlertBox = styled.div`
  display: flex;
  align-items: center;
  background: rgba(80, 80, 80, 0.95);
  padding: 12px 20px;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
`;

const AgentIcon = styled.div`
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: conic-gradient(from 0deg, #ffeb33, #ffc700, #ffeb33);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  flex-shrink: 0;
`;

const AgentIconInner = styled.div`
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(80, 80, 80, 0.95);
`;

const AgentText = styled.div`
  color: white;

  & .title {
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 2px;
  }

  & .message {
    font-size: 12px;
    color: #ccc;
  }
`;

// 수신 메시지 위협 경고 스타일 (채팅 아래 회색 글씨)
const ThreatHint = styled.div<{ riskLevel: string }>`
  font-size: 11px;
  color: ${props => {
    switch(props.riskLevel) {
      case 'CRITICAL': return '#d32f2f';
      case 'HIGH': return '#e65100';
      case 'MEDIUM': return '#f57c00';
      default: return '#888';
    }
  }};
  margin-top: 2px;
  margin-bottom: 4px;
  max-width: 70%;
  line-height: 1.4;
  word-wrap: break-word;

  & .hint-icon {
    margin-right: 4px;
  }
`;

// 시크릿 메시지 링크 스타일
const SecretLink = styled.div`
  position: relative;
  display: inline-block;
  padding: 10px 14px;
  border-radius: 12px;
  margin-bottom: 4px;
  background: linear-gradient(135deg, #ffeb33 0%, #ffc700 100%);
  color: #000;
  cursor: pointer;
  box-shadow: 0px 2px 8px rgba(255, 199, 0, 0.4);
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0px 4px 12px rgba(255, 199, 0, 0.5);
  }

  & .secret-icon {
    display: inline-block;
    margin-right: 6px;
  }

  & .secret-text {
    font-weight: 500;
    font-size: 14px;
  }

  & span.time {
    position: absolute;
    min-width: 65px;
    bottom: -2px;
    color: #666;
  }

  & span.not-read {
    position: absolute;
    min-width: 30px;
    color: #ffec42;
  }
`;

// 시크릿 메시지 아래 에이전트 라벨
const SecretAgentLabel = styled.div`
  font-size: 11px;
  color: #888;
  margin-bottom: 4px;
`;

// 시크릿 메시지 읽음 상태 표시
const SecretViewedLabel = styled.div`
  font-size: 11px;
  color: #888;
  margin-bottom: 7px;

  & .check-icon {
    color: #ffcc00;
    margin-right: 4px;
  }
`;

interface ChatProps {
  msg: string;
  localeTime: string;
  notRead: number;
  content?: string;
  messageType?: 'text' | 'image' | 'secret' | 'agent_alert';
  imageUrl?: string;
  secretId?: string;
  securityAnalysis?: SecurityAnalysis;
  isMine?: boolean;
}

interface FriendChatProps {
  user: UserResponseDto;
  msg: string;
  localeTime: string;
  notRead: number;
  content?: string;
  messageType?: 'text' | 'image' | 'secret';
  imageUrl?: string;
  secretId?: string;
  securityAnalysis?: SecurityAnalysis;
  onImgClick(): void;
}

export const Chat: React.FC<ChatProps> = ({ msg, localeTime, notRead, messageType, imageUrl, secretId, isMine }) => {
  const [showSecretViewer, setShowSecretViewer] = useState(false);
  const [showImageViewer, setShowImageViewer] = useState(false);
  const [secretStatus, setSecretStatus] = useState<SecretMessageStatus | null>(null);

  // 내가 보낸 시크릿 메시지인 경우 읽음 상태 체크
  useEffect(() => {
    if (!isMine || messageType !== 'secret' || !secretId) {
      return;
    }

    let intervalId: ReturnType<typeof setInterval> | null = null;
    let isMounted = true;

    const fetchStatus = async () => {
      try {
        const status = await checkSecretStatus(secretId);
        if (!isMounted) return;

        setSecretStatus(status);

        // 읽음 또는 만료되면 폴링 중단
        if (status.is_viewed || status.is_expired) {
          if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
          }
        }
      } catch (err) {
        console.error('Failed to fetch secret status:', err);
      }
    };

    fetchStatus();
    intervalId = setInterval(fetchStatus, 5000);

    return () => {
      isMounted = false;
      if (intervalId) clearInterval(intervalId);
    };
  }, [isMine, messageType, secretId]);

  // 읽은 시간 포맷
  const formatViewedTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('ko-KR', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 에이전트 알림 메시지인 경우 (채팅방 중앙에 저장되는 메시지)
  if (messageType === 'agent_alert') {
    return (
      <AgentAlertWrapper>
        <AgentAlertBox>
          <AgentIcon>
            <AgentIconInner />
          </AgentIcon>
          <AgentText>
            <div className="title">시크릿 전송 에이전트:</div>
            <div className="message">{msg || '"민감정보를 시크릿 전송으로 보냈어요."'}</div>
          </AgentText>
        </AgentAlertBox>
      </AgentAlertWrapper>
    );
  }

  // 시크릿 메시지인 경우
  if (messageType === 'secret' && secretId) {
    return (
      <>
        <SecretLink onClick={() => setShowSecretViewer(true)}>
          <span className="secret-icon">🔒</span>
          <span className="secret-text">[시크릿문서링크]</span>
          <span className="time" style={{ left: '-70px', textAlign: 'right' }}>{localeTime}</span>
          <span className="not-read" style={{ left: '-35px', bottom: '18px', textAlign: 'right' }}>{notRead > 0 ? notRead : ''}</span>
        </SecretLink>
        <SecretAgentLabel>시크릿전송에이전트</SecretAgentLabel>
        {/* 내가 보낸 시크릿 메시지 - 읽음 상태 표시 */}
        {isMine && secretStatus?.is_viewed && secretStatus.viewed_at && (
          <SecretViewedLabel>
            <span className="check-icon">✓</span>
            읽음 {formatViewedTime(secretStatus.viewed_at)}
          </SecretViewedLabel>
        )}
        {/* 발신자: SecretMessageManager (시간 연장, 삭제 가능) */}
        {showSecretViewer && isMine && (
          <SecretMessageManager
            secretId={secretId}
            onClose={() => setShowSecretViewer(false)}
          />
        )}
        {/* 수신자: SecretMessageViewer (열람만 가능) */}
        {showSecretViewer && !isMine && (
          <SecretMessageViewer
            secretId={secretId}
            onClose={() => setShowSecretViewer(false)}
          />
        )}
      </>
    );
  }

  // 이미지 메시지인 경우
  if (messageType === 'image' && imageUrl) {
    const fullImageUrl = imageUrl.startsWith('http') ? imageUrl : `${HOST}${imageUrl}`;
    return (
      <>
        <ImageWrapper onClick={() => setShowImageViewer(true)}>
          <img src={fullImageUrl} alt="전송된 이미지" />
          <span className="time">{localeTime}</span>
          <span className="not-read">{notRead > 0 ? notRead : ''}</span>
        </ImageWrapper>
        {showImageViewer && (
          <ImageViewerModal
            imageUrl={fullImageUrl}
            onClose={() => setShowImageViewer(false)}
          />
        )}
      </>
    );
  }

  // 텍스트 메시지
  return (
    <ChatWrapper>
      {msg}
      <span className="time">{localeTime}</span>
      <span className="not-read">{notRead > 0 ? notRead : ''}</span>
    </ChatWrapper>
  );
};

// 내가 보낸 채팅
export const MyChat: React.FC<ChatProps> = props => {
  const { content, messageType } = props;

  // 에이전트 알림은 중앙 정렬로 표시
  if (messageType === 'agent_alert') {
    return (
      <React.Fragment>
        {content ? <SeparationBlock content={content} /> : null}
        <Chat {...props} isMine={true} />
      </React.Fragment>
    );
  }

  return (
    <React.Fragment>
      {content ? <SeparationBlock content={content} /> : null}
      <RightBlock>
        <div>
          <Chat {...props} isMine={true} />
        </div>
      </RightBlock>
    </React.Fragment>
  );
};

// 다른 사람이 보낸 채팅 (연속 메시지, 썸네일 없음)
export const FriendChat: React.FC<ChatProps> = props => {
  const { securityAnalysis } = props;
  // 위협 힌트 표시 여부 (LOW가 아닌 경우에만)
  const showHint = securityAnalysis && securityAnalysis.risk_level !== 'LOW';

  return (
    <LeftBlock>
      <div>
        <Chat {...props} />
      </div>
      {showHint && (
        <ThreatHint riskLevel={securityAnalysis!.risk_level}>
          <span className="hint-icon">{getThreatIcon(securityAnalysis!.risk_level)}</span>
          {getThreatHintText(securityAnalysis!)}
        </ThreatHint>
      )}
    </LeftBlock>
  );
};

// 위협 경고 아이콘 헬퍼
const getThreatIcon = (riskLevel: string) => {
  switch(riskLevel) {
    case 'CRITICAL': return '🚨';
    case 'HIGH': return '⚠️';
    case 'MEDIUM': return '⚡';
    default: return '✓';
  }
};

// 위협 힌트 텍스트 (채팅 아래 회색 글씨)
const getThreatHintText = (analysis: SecurityAnalysis) => {
  const { risk_level, reasons, category_name } = analysis;

  // 카테고리가 있으면 표시
  if (category_name && category_name !== '일상 대화' && category_name !== '알 수 없음') {
    if (risk_level === 'CRITICAL') {
      return `이 메시지는 ${category_name} 사기일 수 있어요`;
    } else if (risk_level === 'HIGH') {
      return `${category_name} 패턴이 감지되었어요`;
    } else {
      return `${category_name} 가능성이 있어요`;
    }
  }

  // 이유가 있으면 첫 번째 이유 전체 표시 (말줄임 없음)
  if (reasons && reasons.length > 0) {
    return reasons[0];
  }

  // 기본 메시지
  switch(risk_level) {
    case 'CRITICAL': return '이 메시지는 사기일 수 있어요';
    case 'HIGH': return '주의가 필요한 메시지예요';
    case 'MEDIUM': return '확인이 필요해요';
    default: return '';
  }
};

// 다른 사람이 보냈으며, 프로필 사진을 포함하는 채팅
export const FriendChatWithThumbnail: React.FC<FriendChatProps> = props => {
  const { user, content, onImgClick, securityAnalysis } = props;

  // 위협 힌트 표시 여부 (LOW가 아닌 경우에만)
  const showHint = securityAnalysis && securityAnalysis.risk_level !== 'LOW';

  return (
    <React.Fragment>
      {content ? <SeparationBlock content={content} /> : null}
      <LeftBlock>
        <img
          src={user.profile_img_url || BASE_IMG_URL}
          alt="thumbnail"
          onClick={onImgClick}
        />
        <NameBlock>{user.name}</NameBlock>
        <div>
          <Chat {...props} />
        </div>
        {showHint && (
          <ThreatHint riskLevel={securityAnalysis!.risk_level}>
            <span className="hint-icon">{getThreatIcon(securityAnalysis!.risk_level)}</span>
            {getThreatHintText(securityAnalysis!)}
          </ThreatHint>
        )}
      </LeftBlock>
    </React.Fragment>
  );
};
