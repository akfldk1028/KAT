import React, { useState } from 'react';
import styled from 'styled-components';
import { UserResponseDto } from '~/types/user';
import { BASE_IMG_URL, HOST } from '~/constants';
import { SeparationBlock } from './InfoBlock';
import SecretMessageViewer from './SecretMessageViewer';

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
  & img {
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
  background: conic-gradient(from 0deg, #ff6b9d, #c850c0, #4158d0, #ff6b9d);
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

// 시크릿 메시지 링크 스타일
const SecretLink = styled.div`
  position: relative;
  display: inline-block;
  padding: 10px 14px;
  border-radius: 12px;
  margin-bottom: 7px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  cursor: pointer;
  box-shadow: 0px 2px 8px rgba(102, 126, 234, 0.4);
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0px 4px 12px rgba(102, 126, 234, 0.5);
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

interface ChatProps {
  msg: string;
  localeTime: string;
  notRead: number;
  content?: string;
  messageType?: 'text' | 'image' | 'secret' | 'agent_alert';
  imageUrl?: string;
  secretId?: string;
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
  onImgClick(): void;
}

export const Chat: React.FC<ChatProps> = ({ msg, localeTime, notRead, messageType, imageUrl, secretId }) => {
  const [showSecretViewer, setShowSecretViewer] = useState(false);

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
        {showSecretViewer && (
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
      <ImageWrapper onClick={() => window.open(fullImageUrl, '_blank')}>
        <img src={fullImageUrl} alt="전송된 이미지" />
        <span className="time">{localeTime}</span>
        <span className="not-read">{notRead > 0 ? notRead : ''}</span>
      </ImageWrapper>
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
        <Chat {...props} />
      </React.Fragment>
    );
  }

  return (
    <React.Fragment>
      {content ? <SeparationBlock content={content} /> : null}
      <RightBlock>
        <div>
          <Chat {...props} />
        </div>
      </RightBlock>
    </React.Fragment>
  );
};

// 다른 사람이 보낸 채팅
export const FriendChat: React.FC<ChatProps> = props => {
  return (
    <LeftBlock>
      <div>
        <Chat {...props} />
      </div>
    </LeftBlock>
  );
};

// 다른 사람이 보냈으며, 프로필 사진을 포함하는 채팅
export const FriendChatWithThumbnail: React.FC<FriendChatProps> = props => {
  const { user, content, onImgClick } = props;
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
      </LeftBlock>
    </React.Fragment>
  );
};
